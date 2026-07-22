import logging

from apscheduler.schedulers.background import BackgroundScheduler

from cinema_recs.config import Config
from cinema_recs.ingest import run_ingestion
from cinema_recs.models import Cinema

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

    # main.py already performs one ingestion run synchronously at startup,
    # so the first scheduled run naturally lands one interval later.
    scheduler.add_job(job, "interval", hours=config.refresh_interval_hours)
    scheduler.start()
    return scheduler
