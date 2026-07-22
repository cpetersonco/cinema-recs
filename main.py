import logging
import sys

from cinema_recs.config import load_config
from cinema_recs.ingest import run_ingestion
from cinema_recs.logging_setup import configure_logging
from cinema_recs.scheduler import start_scheduler
from cinema_recs.storage import get_or_create_cinema, init_schema
from cinema_recs.web import create_app

logger = logging.getLogger(__name__)

CINEMA_NAME = "Cinepolis McKinney"
CINEMA_LOCATION = "McKinney, TX (off Highway 121)"


def bootstrap():
    configure_logging()
    config = load_config()
    init_schema(config.db_path)
    cinema = get_or_create_cinema(
        config.db_path, CINEMA_NAME, CINEMA_LOCATION, config.source_url
    )
    return config, cinema


def _log_run(run):
    logger.info(
        "Ingestion run %s finished: outcome=%s showtimes_captured=%d",
        run.id,
        run.outcome,
        run.showtimes_captured,
    )


def main():
    config, cinema = bootstrap()

    if len(sys.argv) > 1 and sys.argv[1] == "ingest-once":
        _log_run(run_ingestion(config.db_path, cinema))
        return

    logger.info("Running one-shot ingestion before starting server")
    _log_run(run_ingestion(config.db_path, cinema))

    start_scheduler(config, cinema)

    app = create_app(config, cinema)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
