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
        letterboxd_username=None,
        letterboxd_rating_threshold=None,
        discord_webhook_url=None,
        notifications_enabled=True,
    )


@pytest.fixture
def cinema(config):
    storage.init_schema(config.db_path)
    return storage.get_or_create_cinema(
        config.db_path, "Cinepolis McKinney", "McKinney, TX", config.source_url
    )


@pytest.fixture
def client(config, cinema):
    app = create_app(config, [cinema])
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


def test_listing_consolidates_multiple_showtimes_for_same_movie_at_same_venue(client, config, cinema):
    # Three showings of the same movie at the same venue on different
    # dates - the listing must render exactly one row for it (feature
    # 010 spec User Story 1), showing the earliest one (Aug 1).
    storage.upsert_showtime(
        config.db_path, cinema.id, "Consolidated Movie", date(2026, 8, 3), time(21, 0),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_showtime(
        config.db_path, cinema.id, "Consolidated Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_showtime(
        config.db_path, cinema.id, "Consolidated Movie", date(2026, 8, 2), time(19, 45),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert response.data.count(b"Consolidated Movie") == 1
    assert b"2026-08-01" in response.data
    assert b"2026-08-03" not in response.data


def test_listing_shows_one_row_per_venue_for_movie_playing_at_multiple_venues(config):
    storage.init_schema(config.db_path)
    cinema_a = storage.get_or_create_cinema(
        config.db_path, "Cinepolis McKinney", "McKinney, TX", "https://example.com/a"
    )
    cinema_b = storage.get_or_create_cinema(
        config.db_path, "Texas Theatre", "Dallas, TX", "https://example.com/b"
    )
    storage.upsert_showtime(
        config.db_path, cinema_a.id, "Shared Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_showtime(
        config.db_path, cinema_b.id, "Shared Movie", date(2026, 8, 2), time(19, 0),
        None, datetime(2026, 8, 1, 10, 0, 0),
    )

    app = create_app(config, [cinema_a, cinema_b])
    app.testing = True
    response = app.test_client().get("/")

    assert response.status_code == 200
    # One row under each venue's section - two total, not merged into one.
    assert response.data.count(b"Shared Movie") == 2


def test_listing_shows_ticket_link_when_present(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Ticketed Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
        ticket_url="https://example.com/tickets/123",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b'href="https://example.com/tickets/123"' in response.data


def test_listing_shows_dash_when_ticket_link_absent(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "No Ticket Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"No Ticket Movie" in response.data
    assert b'href="None"' not in response.data


def test_health_shows_no_runs_yet(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert b"No ingestion runs have completed yet" in response.data


def test_health_shows_app_version_when_set(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "a1b2c3d")

    response = client.get("/health")

    assert response.status_code == 200
    assert b"a1b2c3d" in response.data


def test_health_shows_dev_when_app_version_unset(client, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert b"dev" in response.data


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
    # The Rating column now shows the Letterboxd rating (linked to
    # Letterboxd), not TMDB's average_rating above - feature 010 spec
    # Assumptions/FR-005. TMDB's rating is still stored (used elsewhere)
    # but no longer displayed as "Rating".
    storage.upsert_letterboxd_movie_data(
        config.db_path, "The Great Adventure", tmdb_id=42,
        letterboxd_slug="the-great-adventure", average_rating=4.2,
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Action, Adventure" in response.data
    assert b"/poster.jpg" in response.data
    assert b'href="https://letterboxd.com/film/the-great-adventure/"' in response.data
    assert b"4.2" in response.data


def test_listing_shows_letterboxd_rating_link_when_available(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Rated Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Rated Movie", match_status="matched", tmdb_id=7)
    storage.upsert_letterboxd_movie_data(
        config.db_path, "Rated Movie", tmdb_id=7,
        letterboxd_slug="rated-movie", average_rating=3.8,
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b'<a href="https://letterboxd.com/film/rated-movie/">3.8</a>' in response.data


def test_listing_shows_dash_when_no_letterboxd_match_and_no_tmdb_rating(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Unrated Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Unrated Movie", match_status="matched", tmdb_id=8)
    # No upsert_letterboxd_movie_data call at all - not yet enriched - and
    # no TMDB average_rating stored either, so there is truly no rating to
    # fall back to.

    response = client.get("/")

    assert response.status_code == 200
    assert b"Unrated Movie" in response.data
    assert b"letterboxd.com" not in response.data


def test_listing_falls_back_to_tmdb_rating_when_no_letterboxd_data_yet(client, config, cinema):
    # Feature 002 FR-007 requires the listing to display a rating for
    # every movie with stored TMDB metadata. Feature 010 made the Rating
    # column show the Letterboxd rating when available, which must not
    # regress FR-007 for movies not yet Letterboxd-enriched - they should
    # fall back to the stored TMDB rating (plain text, not linked).
    storage.upsert_showtime(
        config.db_path, cinema.id, "TMDB Only Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(
        config.db_path, "TMDB Only Movie", match_status="matched", tmdb_id=10,
        average_rating=6.9,
    )
    # No upsert_letterboxd_movie_data call at all - not yet enriched.

    response = client.get("/")

    assert response.status_code == 200
    assert b"6.9" in response.data
    assert b"letterboxd.com" not in response.data


def test_listing_shows_dash_when_letterboxd_slug_resolved_but_rating_missing(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Slug Only Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Slug Only Movie", match_status="matched", tmdb_id=9)
    # Slug resolved but the rating fetch itself failed/hasn't completed
    # (research.md §3) - must not show a link with no number.
    storage.upsert_letterboxd_movie_data(
        config.db_path, "Slug Only Movie", tmdb_id=9,
        letterboxd_slug="slug-only-movie", average_rating=None,
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Slug Only Movie" in response.data
    assert b"letterboxd.com" not in response.data


def test_listing_renders_normally_for_unmatched_movie(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Unknown Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Unknown Movie", match_status="unmatched")

    response = client.get("/")

    assert response.status_code == 200
    assert b"Unknown Movie" in response.data


def test_listing_shows_recommended_badge_and_reasons(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Beloved Classic", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Beloved Classic", match_status="matched", tmdb_id=42)
    storage.upsert_movie_recommendation(config.db_path, "Beloved Classic", is_recommended=True, reasons="watchlist,rating")

    response = client.get("/")

    assert response.status_code == 200
    assert "⭐".encode() in response.data
    assert b"watchlist,rating" in response.data


def test_listing_shows_onboarded_list_display_names_in_reasons(client, config, cinema):
    """Feature 013 US3: recommendation reasons name the specific onboarded
    Letterboxd list(s) matched, not a raw internal key."""
    storage.upsert_showtime(
        config.db_path, cinema.id, "Genre Darling", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Genre Darling", match_status="matched", tmdb_id=7)
    storage.upsert_movie_recommendation(
        config.db_path,
        "Genre Darling",
        is_recommended=True,
        reasons="Top 250 Horror Films,Top 250 Animated Films",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Top 250 Horror Films" in response.data
    assert b"Top 250 Animated Films" in response.data
    assert b"best_of:" not in response.data


def test_listing_renders_normally_for_non_recommended_movie(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Ordinary Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(config.db_path, "Ordinary Movie", match_status="matched", tmdb_id=99)
    storage.upsert_movie_recommendation(config.db_path, "Ordinary Movie", is_recommended=False, reasons=None)

    response = client.get("/")

    assert response.status_code == 200
    assert b"Ordinary Movie" in response.data
    assert "⭐".encode() not in response.data


def test_listing_renders_normally_for_not_yet_evaluated_movie(client, config, cinema):
    storage.upsert_showtime(
        config.db_path, cinema.id, "Fresh Movie", date(2026, 8, 1), time(18, 30),
        "Standard", datetime(2026, 8, 1, 10, 0, 0),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Fresh Movie" in response.data
    assert "⭐".encode() not in response.data


def test_health_shows_failure_distinct_from_zero_success(client, config, cinema):
    storage.record_ingestion_run(
        config.db_path, cinema.id, datetime(2026, 8, 1, 10, 0, 0), datetime(2026, 8, 1, 10, 0, 5),
        outcome="failure", showtimes_captured=0, error_message="source unreachable",
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert b"FAILURE" in response.data
    assert b"source unreachable" in response.data


def test_health_shows_partial_outcome_distinct_from_success(client, config, cinema):
    storage.record_ingestion_run(
        config.db_path, cinema.id, datetime(2026, 8, 1, 10, 0, 0), datetime(2026, 8, 1, 10, 0, 5),
        outcome="partial", showtimes_captured=4, error_message="1 showing(s) skipped (missing title or unparseable time)",
    )

    response = client.get("/health")

    assert response.status_code == 200
    assert b"PARTIAL" in response.data
    assert b"1 showing(s) skipped" in response.data
