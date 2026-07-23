import logging
import sys

from cinema_recs.config import load_config
from cinema_recs.enrich import run_enrichment
from cinema_recs.ingest import run_ingestion
from cinema_recs.logging_setup import configure_logging
from cinema_recs.recommend import run_recommendation_evaluation
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


def _run_enrichment(config):
    attempted = run_enrichment(config.db_path, config.tmdb_api_key)
    logger.info("Enrichment pass finished: titles_attempted=%d", attempted)


def _run_recommendation_evaluation(config):
    evaluated = run_recommendation_evaluation(config.db_path, config)
    logger.info("Recommendation evaluation finished: movies_evaluated=%d", evaluated)


def main():
    config, cinema = bootstrap()

    if len(sys.argv) > 1 and sys.argv[1] == "ingest-once":
        _log_run(run_ingestion(config.db_path, cinema))
        _run_enrichment(config)
        _run_recommendation_evaluation(config)
        return

    logger.info("Running one-shot ingestion before starting server")
    _log_run(run_ingestion(config.db_path, cinema))
    _run_enrichment(config)
    _run_recommendation_evaluation(config)

    start_scheduler(config, cinema)

    app = create_app(config, cinema)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
