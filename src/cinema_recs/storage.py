import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
from typing import Iterator, Optional

from cinema_recs.models import (
    Cinema,
    EnrichmentAttempt,
    IngestionRun,
    LetterboxdMovieData,
    MovieMetadata,
    MovieRecommendation,
    NotificationRecord,
    Showtime,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS cinema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    source_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'cinepolis'
);

CREATE TABLE IF NOT EXISTS showtime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cinema_id INTEGER NOT NULL REFERENCES cinema(id),
    movie_title TEXT NOT NULL,
    show_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    format TEXT,
    ticket_url TEXT,
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

CREATE TABLE IF NOT EXISTS notification_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_title TEXT NOT NULL UNIQUE,
    active INTEGER NOT NULL,
    notified_at TEXT,
    last_delivery_outcome TEXT,
    notified_showtime_id INTEGER REFERENCES showtime(id),
    disappearance_alerted INTEGER NOT NULL DEFAULT 0
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
        _migrate_add_showtime_ticket_url(conn)
        _migrate_add_notification_disappearance_columns(conn)
        _migrate_add_cinema_source_type(conn)


def _migrate_add_showtime_ticket_url(conn: sqlite3.Connection) -> None:
    """Add showtime.ticket_url (spec FR-011) to a database created before
    this column existed. A no-op against a fresh database, since
    CREATE TABLE IF NOT EXISTS above already includes it there."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(showtime)")}
    if "ticket_url" not in columns:
        conn.execute("ALTER TABLE showtime ADD COLUMN ticket_url TEXT")


def _migrate_add_notification_disappearance_columns(conn: sqlite3.Connection) -> None:
    """Add notification_record.notified_showtime_id/disappearance_alerted
    (feature 005 spec, Key Entities) to a database created before these
    columns existed. A no-op against a fresh database, since
    CREATE TABLE IF NOT EXISTS above already includes them there."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(notification_record)")}
    if "notified_showtime_id" not in columns:
        conn.execute("ALTER TABLE notification_record ADD COLUMN notified_showtime_id INTEGER")
    if "disappearance_alerted" not in columns:
        conn.execute(
            "ALTER TABLE notification_record ADD COLUMN "
            "disappearance_alerted INTEGER NOT NULL DEFAULT 0"
        )


def _migrate_add_cinema_source_type(conn: sqlite3.Connection) -> None:
    """Add cinema.source_type (feature 011 spec FR-001/FR-004) to a database
    created before this column existed. A no-op against a fresh database,
    since CREATE TABLE IF NOT EXISTS above already includes it there.

    The ALTER TABLE's own DEFAULT 'cinepolis' applies to every pre-existing
    row automatically, but that's only correct for Cinepolis-style rows —
    so this backfills the other two known sources using the same
    substring-matching rules `ingest.py`'s dispatch used to rely on
    (research.md §1). This is the *last* use of that matching logic: it
    runs once, only for rows that predate this column, never as ongoing
    dispatch — new rows always get their source_type explicitly from the
    caller (`get_or_create_cinema`), never inferred.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(cinema)")}
    if "source_type" in columns:
        return

    conn.execute("ALTER TABLE cinema ADD COLUMN source_type TEXT NOT NULL DEFAULT 'cinepolis'")
    conn.execute(
        "UPDATE cinema SET source_type = 'texas_theatre' "
        "WHERE lower(source_url) LIKE '%thetexastheatre.com%' OR lower(name) LIKE '%texas theatre%'"
    )
    conn.execute(
        "UPDATE cinema SET source_type = 'angelika_dallas' "
        "WHERE lower(source_url) LIKE '%angelikafilmcenter.com%' OR lower(name) LIKE '%angelika%'"
    )


def get_or_create_cinema(
    db_path: str, name: str, location: str, source_url: str, source_type: str = "cinepolis"
) -> Cinema:
    """`source_type` identifies which scraper `run_ingestion` uses for this
    cinema (feature 011 spec FR-001) — set explicitly by the caller, never
    inferred from `name`/`source_url`. Defaults to `"cinepolis"` so existing
    callers that don't care about routing (most test fixtures) keep working
    unchanged; every real registration path in this app
    (`ensure_texas_theatre_cinema`, `ensure_angelika_dallas_cinema`,
    `main.py`'s Cinepolis registration) passes it explicitly."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM cinema WHERE name = ? AND location = ?", (name, location)
        ).fetchone()
        if row is not None:
            conn.execute(
                "UPDATE cinema SET source_url = ?, source_type = ? WHERE id = ?",
                (source_url, source_type, row["id"]),
            )
            return Cinema(
                id=row["id"],
                name=row["name"],
                location=row["location"],
                source_url=source_url,
                created_at=datetime.fromisoformat(row["created_at"]),
                source_type=source_type,
            )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cursor = conn.execute(
            "INSERT INTO cinema (name, location, source_url, created_at, source_type) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, location, source_url, now.isoformat(), source_type),
        )
        return Cinema(
            id=cursor.lastrowid,
            name=name,
            location=location,
            source_url=source_url,
            created_at=now,
            source_type=source_type,
        )


def get_cinema_by_name(db_path: str, name: str) -> Optional[Cinema]:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM cinema WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        return Cinema(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            source_url=row["source_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
            source_type=row["source_type"],
        )


def ensure_texas_theatre_cinema(db_path: str) -> Cinema:
    from cinema_recs.config import (
        TEXAS_THEATRE_DEFAULT_URL,
        TEXAS_THEATRE_LOCATION,
        TEXAS_THEATRE_NAME,
    )

    return get_or_create_cinema(
        db_path,
        name=TEXAS_THEATRE_NAME,
        location=TEXAS_THEATRE_LOCATION,
        source_url=TEXAS_THEATRE_DEFAULT_URL,
        source_type="texas_theatre",
    )


def ensure_angelika_dallas_cinema(db_path: str) -> Cinema:
    from cinema_recs.config import (
        ANGELIKA_DALLAS_DEFAULT_URL,
        ANGELIKA_DALLAS_LOCATION,
        ANGELIKA_DALLAS_NAME,
    )

    return get_or_create_cinema(
        db_path,
        name=ANGELIKA_DALLAS_NAME,
        location=ANGELIKA_DALLAS_LOCATION,
        source_url=ANGELIKA_DALLAS_DEFAULT_URL,
        source_type="angelika_dallas",
    )


def ensure_amc_stonebriar_cinema(db_path: str) -> Cinema:
    from cinema_recs.config import (
        AMC_STONEBRIAR_DEFAULT_URL,
        AMC_STONEBRIAR_LOCATION,
        AMC_STONEBRIAR_NAME,
    )

    return get_or_create_cinema(
        db_path,
        name=AMC_STONEBRIAR_NAME,
        location=AMC_STONEBRIAR_LOCATION,
        source_url=AMC_STONEBRIAR_DEFAULT_URL,
        source_type="amc_stonebriar",
    )


def upsert_showtime(
    db_path: str,
    cinema_id: int,
    movie_title: str,
    show_date: date,
    start_time: time,
    format: Optional[str],
    seen_at: datetime,
    ticket_url: Optional[str] = None,
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
                "UPDATE showtime SET last_seen_at = ?, status = 'active', ticket_url = ? WHERE id = ?",
                (seen_at.isoformat(), ticket_url, row["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO showtime
                    (cinema_id, movie_title, show_date, start_time, format,
                     ticket_url, first_seen_at, last_seen_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
                """,
                (
                    cinema_id,
                    movie_title,
                    show_date.isoformat(),
                    start_time.isoformat(),
                    format,
                    ticket_url,
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
        ticket_url=row["ticket_url"],
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
    enriched_at = enriched_at or datetime.now(timezone.utc).replace(tzinfo=None)
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
    attempted_at = attempted_at or datetime.now(timezone.utc).replace(tzinfo=None)
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
    fetched_at = fetched_at or datetime.now(timezone.utc).replace(tzinfo=None)
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
    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
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
    evaluated_at = evaluated_at or datetime.now(timezone.utc).replace(tzinfo=None)
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


def get_next_showtime_for_movie(db_path: str, cinema_id: int, movie_title: str) -> Optional[Showtime]:
    """The movie's single earliest upcoming active showtime (research.md's
    "which showtime's date/time" decision for feature 004's notifications)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM showtime
            WHERE cinema_id = ? AND movie_title = ? AND status = 'active'
            ORDER BY show_date, start_time
            LIMIT 1
            """,
            (cinema_id, movie_title),
        ).fetchone()
        if row is None:
            return None
        return _row_to_showtime(row)


def get_showtime_by_id(db_path: str, showtime_id: int) -> Optional[Showtime]:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM showtime WHERE id = ?", (showtime_id,)).fetchone()
        if row is None:
            return None
        return _row_to_showtime(row)


def get_notification_record(db_path: str, movie_title: str) -> Optional[NotificationRecord]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM notification_record WHERE movie_title = ?", (movie_title,)
        ).fetchone()
        if row is None:
            return None
        return NotificationRecord(
            id=row["id"],
            movie_title=row["movie_title"],
            active=bool(row["active"]),
            notified_at=datetime.fromisoformat(row["notified_at"]) if row["notified_at"] else None,
            last_delivery_outcome=row["last_delivery_outcome"],
            notified_showtime_id=row["notified_showtime_id"],
            disappearance_alerted=bool(row["disappearance_alerted"]),
        )


def upsert_notification_record(
    db_path: str,
    movie_title: str,
    active: bool,
    notified_at: Optional[datetime] = None,
    last_delivery_outcome: Optional[str] = None,
    notified_showtime_id: Optional[int] = None,
    disappearance_alerted: bool = False,
) -> NotificationRecord:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM notification_record WHERE movie_title = ?", (movie_title,)
        ).fetchone()

        params = (
            int(active),
            notified_at.isoformat() if notified_at else None,
            last_delivery_outcome,
            notified_showtime_id,
            int(disappearance_alerted),
        )

        if row is not None:
            conn.execute(
                """
                UPDATE notification_record SET
                    active = ?, notified_at = ?, last_delivery_outcome = ?,
                    notified_showtime_id = ?, disappearance_alerted = ?
                WHERE movie_title = ?
                """,
                params + (movie_title,),
            )
            record_id = row["id"]
        else:
            cursor = conn.execute(
                """
                INSERT INTO notification_record
                    (movie_title, active, notified_at, last_delivery_outcome,
                     notified_showtime_id, disappearance_alerted)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (movie_title,) + params,
            )
            record_id = cursor.lastrowid

        return NotificationRecord(
            id=record_id,
            movie_title=movie_title,
            active=active,
            notified_at=notified_at,
            last_delivery_outcome=last_delivery_outcome,
            notified_showtime_id=notified_showtime_id,
            disappearance_alerted=disappearance_alerted,
        )


def list_active_notification_records(db_path: str) -> list[NotificationRecord]:
    """Notification records currently tracking a referenced showtime for
    disappearance detection (feature 005 spec FR-001)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM notification_record
            WHERE active = 1 AND notified_showtime_id IS NOT NULL
            """
        ).fetchall()
        return [
            NotificationRecord(
                id=row["id"],
                movie_title=row["movie_title"],
                active=bool(row["active"]),
                notified_at=datetime.fromisoformat(row["notified_at"]) if row["notified_at"] else None,
                last_delivery_outcome=row["last_delivery_outcome"],
                notified_showtime_id=row["notified_showtime_id"],
                disappearance_alerted=bool(row["disappearance_alerted"]),
            )
            for row in rows
        ]
