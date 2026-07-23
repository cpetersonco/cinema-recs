import logging
from datetime import datetime, timezone

from cinema_recs import storage
from cinema_recs.models import Cinema, IngestionRun
from cinema_recs.scraper import (
    scrape_amc_stonebriar_showtimes,
    scrape_angelika_dallas_showtimes,
    scrape_cinemark_west_plano_showtimes,
    scrape_showtimes,
    scrape_texas_theatre_showtimes,
)

logger = logging.getLogger(__name__)


def run_ingestion(db_path: str, cinema: Cinema) -> IngestionRun:
    started_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Explicit mapping from Cinema.source_type to its scraper (feature 011
    # spec FR-001) — replaces the old substring-matching dispatch that
    # silently fell back to the Cinepolis scraper for any unrecognized
    # source (spec FR-003). Built fresh per call (not at module load) so it
    # resolves each scraper name through this module's own current
    # namespace — required for tests to monkeypatch
    # `cinema_recs.ingest.scrape_showtimes` etc. and have dispatch actually
    # use the patched version, the same way the module-level names were
    # already re-resolved per call under the old if/elif/else dispatch.
    scrapers_by_source_type = {
        "cinepolis": scrape_showtimes,
        "texas_theatre": scrape_texas_theatre_showtimes,
        "angelika_dallas": scrape_angelika_dallas_showtimes,
        "amc_stonebriar": scrape_amc_stonebriar_showtimes,
        "cinemark_west_plano": scrape_cinemark_west_plano_showtimes,
    }

    try:
        scraper = scrapers_by_source_type.get(cinema.source_type)
        if scraper is None:
            raise ValueError(f"Unrecognized cinema source_type: {cinema.source_type!r}")
        result = scraper(cinema.source_url)
    except Exception as exc:  # noqa: BLE001 - any scrape failure is recorded, not raised
        logger.exception("Ingestion run failed for cinema %s", cinema.id)
        finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
        return storage.record_ingestion_run(
            db_path,
            cinema_id=cinema.id,
            started_at=started_at,
            finished_at=finished_at,
            outcome="failure",
            showtimes_captured=0,
            error_message=str(exc),
        )

    showtimes = result.showtimes
    logger.info(
        "Scrape for cinema %s returned %d showtime(s), %d reported by the source, complete=%s",
        cinema.id, len(showtimes), result.reported_count, result.complete,
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
            ticket_url=showtime.ticket_url,
        )

    finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
    outcome = "success"
    error_message = None
    skipped_count = result.reported_count - len(showtimes)

    if not result.complete:
        # The fetch stopped before reaching the source's own end of its
        # published calendar (e.g. a request failed partway through a
        # multi-date/month walk). Trusting this run's partial results as
        # "nothing else is published" would wrongly stale-mark real
        # showtimes in the unreached pages/dates, so stale-marking is
        # skipped entirely for this run.
        outcome = "partial" if showtimes else "failure"
        reason = result.incomplete_reason or "full-window fetch stopped early"
        error_message = f"{reason} ({len(showtimes)} showing(s) captured before it stopped)"
        logger.warning(
            "Ingestion run for cinema %s did not complete its full-window fetch: %s",
            cinema.id, error_message,
        )
    else:
        stale_count = storage.mark_stale_showtimes(db_path, cinema.id, started_at)
        if stale_count:
            logger.info("Marked %d showtime(s) stale for cinema %s", stale_count, cinema.id)

        if not showtimes:
            logger.warning(
                "Ingestion run for cinema %s completed with zero showtimes found", cinema.id
            )
        elif skipped_count > 0:
            # Source was reachable and most data came through, but some entries
            # were dropped during parsing (missing movie title / unparseable
            # time) rather than genuinely absent from the source.
            outcome = "partial"
            error_message = f"{skipped_count} showing(s) skipped (missing title or unparseable time)"
            logger.warning(
                "Ingestion run for cinema %s completed partially: %s", cinema.id, error_message
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
