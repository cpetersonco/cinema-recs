from datetime import date, time, timedelta
from unittest.mock import patch

import pytest

from cinema_recs import storage
from cinema_recs.config import Config
from cinema_recs.ingest import run_ingestion
from cinema_recs.notify import run_notifications
from cinema_recs.scraper import ScrapedShowtime, ScrapeResult

# Feature 009, User Story 2: a full-window ingestion run must not treat a
# showtime dated well beyond "tomorrow" as gone just because a narrower
# fetch wouldn't have re-touched it - and, when a showtime genuinely
# disappears from a complete full-window fetch, feature 005's existing
# cancellation/reschedule notification flow must still fire exactly as
# before.


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_full_window_notifications.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def cinema(db_path):
    return storage.get_or_create_cinema(
        db_path, "Cinepolis McKinney", "McKinney, TX", "https://example.com"
    )


def _config(tmp_path):
    return Config(
        source_url="https://example.com",
        refresh_interval_hours=3,
        data_dir=str(tmp_path),
        port=8080,
        tmdb_api_key="test-tmdb-key",
        letterboxd_username=None,
        letterboxd_rating_threshold=None,
        discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        notifications_enabled=True,
    )


def _recommend(db_path, title):
    storage.upsert_movie_metadata(db_path, title, match_status="matched", tmdb_id=42)
    storage.upsert_movie_recommendation(db_path, title, is_recommended=True, reasons="watchlist")


@patch("cinema_recs.notify.send_notification")
def test_far_out_showtime_survives_full_window_ingestion_without_false_alert(
    mock_send, db_path, cinema, tmp_path, monkeypatch
):
    far_out_date = date(2026, 8, 1) + timedelta(days=21)
    showtime = ScrapedShowtime("Far Out Movie", far_out_date, time(18, 0), None, None)

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(showtimes=[showtime], reported_count=1, complete=True),
    )
    run_ingestion(db_path, cinema)
    _recommend(db_path, "Far Out Movie")

    config = _config(tmp_path)
    sent_first = run_notifications(db_path, cinema.id, config)
    assert sent_first == 1
    mock_send.reset_mock()

    # A second, independent full-window ingestion run still finds the same
    # far-out showtime (the source never stopped publishing it) - it must
    # stay active, not get wrongly stale-marked and alerted on.
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(showtimes=[showtime], reported_count=1, complete=True),
    )
    run_ingestion(db_path, cinema)

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].status == "active"

    sent_second = run_notifications(db_path, cinema.id, config)
    assert sent_second == 0
    mock_send.assert_not_called()


@patch("cinema_recs.notify.send_notification")
def test_genuinely_removed_showtime_still_triggers_cancellation_alert(
    mock_send, db_path, cinema, tmp_path, monkeypatch
):
    original = ScrapedShowtime("Movie Gone", date(2026, 8, 1), time(18, 0), None, None)

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(showtimes=[original], reported_count=1, complete=True),
    )
    run_ingestion(db_path, cinema)
    _recommend(db_path, "Movie Gone")

    config = _config(tmp_path)
    run_notifications(db_path, cinema.id, config)
    mock_send.reset_mock()

    # A complete full-window run no longer finds the showtime anywhere -
    # it's genuinely gone, so it should be marked stale and a cancellation
    # alert should still fire, exactly as feature 005 already guarantees.
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(showtimes=[], reported_count=0, complete=True),
    )
    run_ingestion(db_path, cinema)

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert active == []

    sent = run_notifications(db_path, cinema.id, config)
    assert sent == 1
    mock_send.assert_called_once()
    _, message = mock_send.call_args[0]
    assert "cancelled" in message.lower()
    assert "Movie Gone" in message
