import logging

from apscheduler.schedulers.background import BackgroundScheduler

from cinema_recs.config import Config
from cinema_recs.enrich import run_enrichment
from cinema_recs.ingest import run_ingestion
from cinema_recs.models import Cinema
from cinema_recs.recommend import run_recommendation_evaluation

logger = logging.getLogger(__name__)


def start_scheduler(config: Config, cinema: Cinema) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    def job():
        run = run_ingestion(config.db_path, cinema)
        logger.info(
            "Scheduled ingestion run %s finished: outcome=%s showtimes_captured=%d",
            run.id,
            run.outcome,
            run.showtimes_captured,
        )

        attempted = run_enrichment(config.db_path, config.tmdb_api_key)
        logger.info("Scheduled enrichment pass finished: titles_attempted=%d", attempted)

        # Recommendation evaluation must run after enrichment/ingestion each
        # cycle (not just once at startup) so watchlist changes and newly
        # ingested movies are reflected without a container restart
        # (spec FR-002/FR-007/SC-002).
        evaluated = run_recommendation_evaluation(config.db_path, config)
        logger.info("Scheduled recommendation evaluation finished: movies_evaluated=%d", evaluated)

    # main.py already performs one ingestion/enrichment/evaluation cycle
    # synchronously at startup, so the first scheduled run naturally lands
    # one interval later.
    scheduler.add_job(job, "interval", hours=config.refresh_interval_hours)
    scheduler.start()
    return scheduler
