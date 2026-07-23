import logging
import sys

from cinema_recs.config import load_config
from cinema_recs.enrich import run_enrichment
from cinema_recs.ingest import run_ingestion
from cinema_recs.logging_setup import configure_logging
from cinema_recs.notify import run_notifications
from cinema_recs.recommend import run_recommendation_evaluation
from cinema_recs.scheduler import start_scheduler
from cinema_recs.storage import (
    ensure_amc_stonebriar_cinema,
    ensure_angelika_dallas_cinema,
    ensure_cinemark_west_plano_cinema,
    ensure_texas_theatre_cinema,
    get_or_create_cinema,
    init_schema,
)
from cinema_recs.web import create_app

logger = logging.getLogger(__name__)

CINEMA_NAME = "Cinepolis McKinney"
CINEMA_LOCATION = "McKinney, TX (off Highway 121)"


def bootstrap():
    configure_logging()
    config = load_config()
    init_schema(config.db_path)
    cinepolis = get_or_create_cinema(
        config.db_path, CINEMA_NAME, CINEMA_LOCATION, config.source_url, source_type="cinepolis"
    )
    texas_theatre = ensure_texas_theatre_cinema(config.db_path)
    angelika_dallas = ensure_angelika_dallas_cinema(config.db_path)
    amc_stonebriar = ensure_amc_stonebriar_cinema(config.db_path)
    cinemark_west_plano = ensure_cinemark_west_plano_cinema(config.db_path)
    cinemas = [cinepolis, texas_theatre, angelika_dallas, amc_stonebriar, cinemark_west_plano]
    return config, cinemas


def _log_run(run, cinema):
    logger.info(
        "Ingestion run %s finished for cinema %r: outcome=%s showtimes_captured=%d",
        run.id,
        cinema.name,
        run.outcome,
        run.showtimes_captured,
    )


def _run_ingestion_all(config, cinemas):
    for cinema in cinemas:
        _log_run(run_ingestion(config.db_path, cinema), cinema)


def _run_enrichment(config):
    attempted = run_enrichment(config.db_path, config.tmdb_api_key)
    logger.info("Enrichment pass finished: titles_attempted=%d", attempted)


def _run_recommendation_evaluation(config):
    evaluated = run_recommendation_evaluation(config.db_path, config)
    logger.info("Recommendation evaluation finished: movies_evaluated=%d", evaluated)


def _run_notifications_all(config, cinemas):
    for cinema in cinemas:
        sent = run_notifications(config.db_path, cinema.id, config)
        logger.info(
            "Notification evaluation finished for cinema %r: notifications_sent=%d",
            cinema.name,
            sent,
        )


def main():
    config, cinemas = bootstrap()

    if len(sys.argv) > 1 and sys.argv[1] == "ingest-once":
        _run_ingestion_all(config, cinemas)
        _run_enrichment(config)
        _run_recommendation_evaluation(config)
        _run_notifications_all(config, cinemas)
        return

    logger.info("Running one-shot ingestion before starting server")
    _run_ingestion_all(config, cinemas)
    _run_enrichment(config)
    _run_recommendation_evaluation(config)
    _run_notifications_all(config, cinemas)

    start_scheduler(config, cinemas)

    app = create_app(config, cinemas)
    app.run(host="0.0.0.0", port=config.port)


if __name__ == "__main__":
    main()
