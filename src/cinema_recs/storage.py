import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time
from typing import Iterator, Optional

from cinema_recs.models import Cinema, IngestionRun, Showtime

SCHEMA = """
CREATE TABLE IF NOT EXISTS cinema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    source_url TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS showtime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cinema_id INTEGER NOT NULL REFERENCES cinema(id),
    movie_title TEXT NOT NULL,
    show_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    format TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE (cinema_id, movie_title, show_date, start_time, format)
);

CREATE TABLE IF NOT EXISTS ingestion_run (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cinema_id INTEGER NOT NULL REFERENCES cinema(id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    outcome TEXT NOT NULL,
    showtimes_captured INTEGER NOT NULL,
    error_message TEXT
);
"""


@contextmanager
def get_connection(db_path: str) -> Iterator[sqlite3.Connection]:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema(db_path: str) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)


def get_or_create_cinema(
    db_path: str, name: str, location: str, source_url: str
) -> Cinema:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM cinema WHERE name = ? AND location = ?", (name, location)
        ).fetchone()
        if row is not None:
            conn.execute(
                "UPDATE cinema SET source_url = ? WHERE id = ?", (source_url, row["id"])
            )
            return Cinema(
                id=row["id"],
                name=row["name"],
                location=row["location"],
                source_url=source_url,
                created_at=datetime.fromisoformat(row["created_at"]),
            )

        now = datetime.utcnow()
        cursor = conn.execute(
            "INSERT INTO cinema (name, location, source_url, created_at) VALUES (?, ?, ?, ?)",
            (name, location, source_url, now.isoformat()),
        )
        return Cinema(
            id=cursor.lastrowid,
            name=name,
            location=location,
            source_url=source_url,
            created_at=now,
        )


def upsert_showtime(
    db_path: str,
    cinema_id: int,
    movie_title: str,
    show_date: date,
    start_time: time,
    format: Optional[str],
    seen_at: datetime,
) -> None:
    """Insert a newly-observed showtime, or refresh last_seen_at/status if it
    already exists (whether previously active or stale)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT id FROM showtime
            WHERE cinema_id = ? AND movie_title = ? AND show_date = ?
              AND start_time = ? AND (format IS ? OR format = ?)
            """,
            (cinema_id, movie_title, show_date.isoformat(), start_time.isoformat(), format, format),
        ).fetchone()

        if row is not None:
            conn.execute(
                "UPDATE showtime SET last_seen_at = ?, status = 'active' WHERE id = ?",
                (seen_at.isoformat(), row["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO showtime
                    (cinema_id, movie_title, show_date, start_time, format,
                     first_seen_at, last_seen_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                """,
                (
                    cinema_id,
                    movie_title,
                    show_date.isoformat(),
                    start_time.isoformat(),
                    format,
                    seen_at.isoformat(),
                    seen_at.isoformat(),
                ),
            )


def mark_stale_showtimes(db_path: str, cinema_id: int, seen_at: datetime) -> int:
    """Mark any 'active' showtime not touched by the current run (last_seen_at
    older than seen_at) as 'stale'. Returns the number of rows affected."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            UPDATE showtime SET status = 'stale'
            WHERE cinema_id = ? AND status = 'active' AND last_seen_at < ?
            """,
            (cinema_id, seen_at.isoformat()),
        )
        return cursor.rowcount


def list_active_showtimes(db_path: str, cinema_id: int) -> list[Showtime]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM showtime
            WHERE cinema_id = ? AND status = 'active'
            ORDER BY show_date, start_time
            """,
            (cinema_id,),
        ).fetchall()
        return [_row_to_showtime(row) for row in rows]


def _row_to_showtime(row: sqlite3.Row) -> Showtime:
    return Showtime(
        id=row["id"],
        cinema_id=row["cinema_id"],
        movie_title=row["movie_title"],
        show_date=date.fromisoformat(row["show_date"]),
        start_time=time.fromisoformat(row["start_time"]),
        format=row["format"],
        first_seen_at=datetime.fromisoformat(row["first_seen_at"]),
        last_seen_at=datetime.fromisoformat(row["last_seen_at"]),
        status=row["status"],
    )


def record_ingestion_run(
    db_path: str,
    cinema_id: int,
    started_at: datetime,
    finished_at: datetime,
    outcome: str,
    showtimes_captured: int,
    error_message: Optional[str] = None,
) -> IngestionRun:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO ingestion_run
                (cinema_id, started_at, finished_at, outcome, showtimes_captured, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                cinema_id,
                started_at.isoformat(),
                finished_at.isoformat(),
                outcome,
                showtimes_captured,
                error_message,
            ),
        )
        return IngestionRun(
            id=cursor.lastrowid,
            cinema_id=cinema_id,
            started_at=started_at,
            finished_at=finished_at,
            outcome=outcome,
            showtimes_captured=showtimes_captured,
            error_message=error_message,
        )


def get_latest_ingestion_run(db_path: str, cinema_id: int) -> Optional[IngestionRun]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM ingestion_run
            WHERE cinema_id = ?
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (cinema_id,),
        ).fetchone()
        if row is None:
            return None
        return IngestionRun(
            id=row["id"],
            cinema_id=row["cinema_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            outcome=row["outcome"],
            showtimes_captured=row["showtimes_captured"],
            error_message=row["error_message"],
        )
