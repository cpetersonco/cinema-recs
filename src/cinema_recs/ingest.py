import logging
from datetime import datetime

from cinema_recs import storage
from cinema_recs.models import Cinema, IngestionRun
from cinema_recs.scraper import scrape_showtimes

logger = logging.getLogger(__name__)


def run_ingestion(db_path: str, cinema: Cinema) -> IngestionRun:
    started_at = datetime.utcnow()

    try:
        showtimes = scrape_showtimes(cinema.source_url)
    except Exception as exc:  # noqa: BLE001 - any scrape failure is recorded, not raised
        logger.exception("Ingestion run failed for cinema %s", cinema.id)
        finished_at = datetime.utcnow()
        return storage.record_ingestion_run(
            db_path,
            cinema_id=cinema.id,
            started_at=started_at,
            finished_at=finished_at,
            outcome="failure",
            showtimes_captured=0,
            error_message=str(exc),
        )

    for showtime in showtimes:
        storage.upsert_showtime(
            db_path,
            cinema_id=cinema.id,
            movie_title=showtime.movie_title,
            show_date=showtime.show_date,
            start_time=showtime.start_time,
            format=showtime.format,
            seen_at=started_at,
        )

    stale_count = storage.mark_stale_showtimes(db_path, cinema.id, started_at)
    if stale_count:
        logger.info("Marked %d showtime(s) stale for cinema %s", stale_count, cinema.id)

    finished_at = datetime.utcnow()
    outcome = "success"
    error_message = None
    if not showtimes:
        logger.warning(
            "Ingestion run for cinema %s completed with zero showtimes found", cinema.id
        )

    return storage.record_ingestion_run(
        db_path,
        cinema_id=cinema.id,
        started_at=started_at,
        finished_at=finished_at,
        outcome=outcome,
        showtimes_captured=len(showtimes),
        error_message=error_message,
    )
