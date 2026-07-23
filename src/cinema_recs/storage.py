import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time
from typing import Iterator, Optional

from cinema_recs.models import (
    Cinema,
    EnrichmentAttempt,
    IngestionRun,
    LetterboxdMovieData,
    MovieMetadata,
    MovieRecommendation,
    Showtime,
)

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

CREATE TABLE IF NOT EXISTS movie_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_title TEXT NOT NULL UNIQUE,
    match_status TEXT NOT NULL,
    tmdb_id INTEGER,
    tmdb_title TEXT,
    genres TEXT,
    overview TEXT,
    release_year INTEGER,
    average_rating REAL,
    runtime_minutes INTEGER,
    poster_path TEXT,
    last_enriched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enrichment_attempt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_title TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    outcome TEXT NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS letterboxd_movie_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_title TEXT NOT NULL UNIQUE,
    tmdb_id INTEGER NOT NULL,
    letterboxd_slug TEXT,
    average_rating REAL,
    fetched_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS letterboxd_reference_list (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_key TEXT NOT NULL,
    film_slug TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE (list_key, film_slug)
);

CREATE TABLE IF NOT EXISTS movie_recommendation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_title TEXT NOT NULL UNIQUE,
    is_recommended INTEGER NOT NULL,
    reasons TEXT,
    evaluated_at TEXT NOT NULL
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


def list_distinct_movie_titles_without_metadata(db_path: str) -> list[str]:
    """Distinct showtime movie titles that have no movie_metadata row yet
    (per T010: these are the titles enrichment still needs to attempt)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT s.movie_title FROM showtime s
            LEFT JOIN movie_metadata m ON m.movie_title = s.movie_title
            WHERE m.id IS NULL
            """
        ).fetchall()
        return [row["movie_title"] for row in rows]


def get_movie_metadata(db_path: str, movie_title: str) -> Optional[MovieMetadata]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM movie_metadata WHERE movie_title = ?", (movie_title,)
        ).fetchone()
        if row is None:
            return None
        return _row_to_movie_metadata(row)


def _row_to_movie_metadata(row: sqlite3.Row) -> MovieMetadata:
    return MovieMetadata(
        id=row["id"],
        movie_title=row["movie_title"],
        match_status=row["match_status"],
        tmdb_id=row["tmdb_id"],
        tmdb_title=row["tmdb_title"],
        genres=row["genres"],
        overview=row["overview"],
        release_year=row["release_year"],
        average_rating=row["average_rating"],
        runtime_minutes=row["runtime_minutes"],
        poster_path=row["poster_path"],
        last_enriched_at=datetime.fromisoformat(row["last_enriched_at"]),
    )


def upsert_movie_metadata(
    db_path: str,
    movie_title: str,
    match_status: str,
    tmdb_id: Optional[int] = None,
    tmdb_title: Optional[str] = None,
    genres: Optional[str] = None,
    overview: Optional[str] = None,
    release_year: Optional[int] = None,
    average_rating: Optional[float] = None,
    runtime_minutes: Optional[int] = None,
    poster_path: Optional[str] = None,
    enriched_at: Optional[datetime] = None,
) -> MovieMetadata:
    """Insert or replace the cached MovieMetadata row for movie_title (spec
    FR-003's caching requirement: one row per distinct ingested title)."""
    enriched_at = enriched_at or datetime.utcnow()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM movie_metadata WHERE movie_title = ?", (movie_title,)
        ).fetchone()

        params = (
            match_status,
            tmdb_id,
            tmdb_title,
            genres,
            overview,
            release_year,
            average_rating,
            runtime_minutes,
            poster_path,
            enriched_at.isoformat(),
        )

        if row is not None:
            conn.execute(
                """
                UPDATE movie_metadata SET
                    match_status = ?, tmdb_id = ?, tmdb_title = ?, genres = ?,
                    overview = ?, release_year = ?, average_rating = ?,
                    runtime_minutes = ?, poster_path = ?, last_enriched_at = ?
                WHERE movie_title = ?
                """,
                params + (movie_title,),
            )
            metadata_id = row["id"]
        else:
            cursor = conn.execute(
                """
                INSERT INTO movie_metadata
                    (movie_title, match_status, tmdb_id, tmdb_title, genres,
                     overview, release_year, average_rating, runtime_minutes,
                     poster_path, last_enriched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (movie_title,) + params,
            )
            metadata_id = cursor.lastrowid

        return MovieMetadata(
            id=metadata_id,
            movie_title=movie_title,
            match_status=match_status,
            tmdb_id=tmdb_id,
            tmdb_title=tmdb_title,
            genres=genres,
            overview=overview,
            release_year=release_year,
            average_rating=average_rating,
            runtime_minutes=runtime_minutes,
            poster_path=poster_path,
            last_enriched_at=enriched_at,
        )


def record_enrichment_attempt(
    db_path: str,
    movie_title: str,
    outcome: str,
    attempted_at: Optional[datetime] = None,
    error_message: Optional[str] = None,
) -> EnrichmentAttempt:
    attempted_at = attempted_at or datetime.utcnow()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO enrichment_attempt (movie_title, attempted_at, outcome, error_message)
            VALUES (?, ?, ?, ?)
            """,
            (movie_title, attempted_at.isoformat(), outcome, error_message),
        )
        return EnrichmentAttempt(
            id=cursor.lastrowid,
            movie_title=movie_title,
            attempted_at=attempted_at,
            outcome=outcome,
            error_message=error_message,
        )


def list_distinct_matched_movie_titles_without_letterboxd_data(db_path: str) -> list[str]:
    """Matched (feature 002) movie titles with no letterboxd_movie_data row
    yet — these are the titles recommendation evaluation still needs to
    resolve against Letterboxd (spec FR-004/FR-012)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT m.movie_title FROM movie_metadata m
            LEFT JOIN letterboxd_movie_data l ON l.movie_title = m.movie_title
            WHERE m.match_status = 'matched' AND l.id IS NULL
            """
        ).fetchall()
        return [row["movie_title"] for row in rows]


def list_matched_movie_titles(db_path: str) -> list[str]:
    """All feature-002-matched movie titles — the full set recommendation
    evaluation must (re)compute a status for each cycle."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT movie_title FROM movie_metadata WHERE match_status = 'matched'"
        ).fetchall()
        return [row["movie_title"] for row in rows]


def get_letterboxd_movie_data(db_path: str, movie_title: str) -> Optional[LetterboxdMovieData]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM letterboxd_movie_data WHERE movie_title = ?", (movie_title,)
        ).fetchone()
        if row is None:
            return None
        return LetterboxdMovieData(
            id=row["id"],
            movie_title=row["movie_title"],
            tmdb_id=row["tmdb_id"],
            letterboxd_slug=row["letterboxd_slug"],
            average_rating=row["average_rating"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
        )


def upsert_letterboxd_movie_data(
    db_path: str,
    movie_title: str,
    tmdb_id: int,
    letterboxd_slug: Optional[str],
    average_rating: Optional[float],
    fetched_at: Optional[datetime] = None,
) -> LetterboxdMovieData:
    fetched_at = fetched_at or datetime.utcnow()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM letterboxd_movie_data WHERE movie_title = ?", (movie_title,)
        ).fetchone()

        params = (tmdb_id, letterboxd_slug, average_rating, fetched_at.isoformat())

        if row is not None:
            conn.execute(
                """
                UPDATE letterboxd_movie_data SET
                    tmdb_id = ?, letterboxd_slug = ?, average_rating = ?, fetched_at = ?
                WHERE movie_title = ?
                """,
                params + (movie_title,),
            )
            data_id = row["id"]
        else:
            cursor = conn.execute(
                """
                INSERT INTO letterboxd_movie_data
                    (movie_title, tmdb_id, letterboxd_slug, average_rating, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (movie_title,) + params,
            )
            data_id = cursor.lastrowid

        return LetterboxdMovieData(
            id=data_id,
            movie_title=movie_title,
            tmdb_id=tmdb_id,
            letterboxd_slug=letterboxd_slug,
            average_rating=average_rating,
            fetched_at=fetched_at,
        )


def get_reference_list_slugs(db_path: str, list_key: str) -> set[str]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT film_slug FROM letterboxd_reference_list WHERE list_key = ?", (list_key,)
        ).fetchall()
        return {row["film_slug"] for row in rows}


def replace_reference_list_slugs(db_path: str, list_key: str, slugs: set[str]) -> None:
    """Atomically replace all cached slugs for list_key. Only call this on a
    *successful* fetch — on failure, leave the existing cache untouched
    rather than treating the list as empty (data-model.md's resilience
    rule for FR-002/FR-007's periodic re-evaluation requirement)."""
    fetched_at = datetime.utcnow().isoformat()
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM letterboxd_reference_list WHERE list_key = ?", (list_key,))
        conn.executemany(
            """
            INSERT INTO letterboxd_reference_list (list_key, film_slug, fetched_at)
            VALUES (?, ?, ?)
            """,
            [(list_key, slug, fetched_at) for slug in slugs],
        )


def get_movie_recommendation(db_path: str, movie_title: str) -> Optional[MovieRecommendation]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM movie_recommendation WHERE movie_title = ?", (movie_title,)
        ).fetchone()
        if row is None:
            return None
        return MovieRecommendation(
            id=row["id"],
            movie_title=row["movie_title"],
            is_recommended=bool(row["is_recommended"]),
            reasons=row["reasons"],
            evaluated_at=datetime.fromisoformat(row["evaluated_at"]),
        )


def upsert_movie_recommendation(
    db_path: str,
    movie_title: str,
    is_recommended: bool,
    reasons: Optional[str] = None,
    evaluated_at: Optional[datetime] = None,
) -> MovieRecommendation:
    evaluated_at = evaluated_at or datetime.utcnow()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM movie_recommendation WHERE movie_title = ?", (movie_title,)
        ).fetchone()

        params = (int(is_recommended), reasons, evaluated_at.isoformat())

        if row is not None:
            conn.execute(
                """
                UPDATE movie_recommendation SET
                    is_recommended = ?, reasons = ?, evaluated_at = ?
                WHERE movie_title = ?
                """,
                params + (movie_title,),
            )
            rec_id = row["id"]
        else:
            cursor = conn.execute(
                """
                INSERT INTO movie_recommendation (movie_title, is_recommended, reasons, evaluated_at)
                VALUES (?, ?, ?, ?)
                """,
                (movie_title,) + params,
            )
            rec_id = cursor.lastrowid

        return MovieRecommendation(
            id=rec_id,
            movie_title=movie_title,
            is_recommended=is_recommended,
            reasons=reasons,
            evaluated_at=evaluated_at,
        )
