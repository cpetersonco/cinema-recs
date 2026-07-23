from datetime import date, datetime, time

import pytest

from cinema_recs import storage
from cinema_recs.config import Config
from cinema_recs.web import create_app


@pytest.fixture
def config(tmp_path):
    return Config(
        source_url="https://example.com",
        refresh_interval_hours=3,
        data_dir=str(tmp_path),
        port=8080,
        tmdb_api_key="test-tmdb-key",
    )


@pytest.fixture
def cinema(config):
    storage.init_schema(config.db_path)
    return storage.get_or_create_cinema(
        config.db_path, "Cinepolis McKinney", "McKinney, TX", config.source_url
    )


@pytest.fixture
def client(config, cinema):
    app = create_app(config, cinema)
    app.testing = True
    return app.test_client()


def test_listing_shows_empty_state_when_no_showtimes(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"No showtimes ingested yet" in response.data


def test_listing_shows_ingested_showtimes(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "The Great Adventure", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"The Great Adventure" in response.data
    assert b"Standard" in response.data


def test_health_shows_no_runs_yet(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert b"No ingestion runs have completed yet" in response.data


def test_health_shows_success_outcome(client, config, cinema):
    storage.record_ingestion_run(
        config.db_path, cinema.id, datetime(2026, 8, 1, 10, 0, 0), datetime(2026, 8, 1, 10, 0, 5),
        outcome="success", showtimes_captured=5,
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert b"SUCCESS" in response.data
    assert b"5" in response.data


def test_listing_shows_enriched_fields_for_matched_movie(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "The Great Adventure", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(
        config.db_path, "The Great Adventure", match_status="matched", tmdb_id=42,
        tmdb_title="The Great Adventure", genres="Action, Adventure", average_rating=7.5,
        poster_path="/poster.jpg",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Action, Adventure" in response.data
    assert b"7.5" in response.data
    assert b"/poster.jpg" in response.data


def test_listing_renders_normally_for_unmatched_movie(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Unknown Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Unknown Movie", match_status="unmatched")

    response = client.get("/")

    assert response.status_code == 200
    assert b"Unknown Movie" in response.data


def test_health_shows_failure_distinct_from_zero_success(client, config, cinema):
    storage.record_ingestion_run(
        config.db_path, cinema.id, datetime(2026, 8, 1, 10, 0, 0), datetime(2026, 8, 1, 10, 0, 5),
        outcome="failure", showtimes_captured=0, error_message="source unreachable",
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert b"FAILURE" in response.data
    assert b"source unreachable" in response.data
