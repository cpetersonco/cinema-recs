from datetime import date, datetime, time
from unittest.mock import patch

import pytest

from cinema_recs import storage
from cinema_recs.config import Config
from cinema_recs.notify import run_notifications


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def cinema(db_path):
    return storage.get_or_create_cinema(
        db_path, "Cinepolis McKinney", "McKinney, TX", "https://example.com"
    )


def _config(tmp_path, webhook_url="https://discord.com/api/webhooks/123/abc", enabled=True):
    return Config(
        source_url="https://example.com",
        refresh_interval_hours=3,
        data_dir=str(tmp_path),
        port=8080,
        tmdb_api_key="test-tmdb-key",
        letterboxd_username=None,
        letterboxd_rating_threshold=None,
        discord_webhook_url=webhook_url,
        notifications_enabled=enabled,
    )


def _seed_recommended_movie(db_path, cinema, title, ticket_url=None, reasons="watchlist"):
    storage.upsert_showtime(
        db_path, cinema.id, title, date(2026, 8, 1), time(18, 0), None,
        datetime(2026, 8, 1, 10, 0, 0), ticket_url=ticket_url,
    )
    storage.upsert_movie_metadata(db_path, title, match_status="matched", tmdb_id=42)
    storage.upsert_movie_recommendation(db_path, title, is_recommended=True, reasons=reasons)


@patch("cinema_recs.notify.send_notification")
def test_newly_recommended_movie_triggers_notification(mock_send, db_path, cinema, tmp_path):
    _seed_recommended_movie(db_path, cinema, "The Great Adventure", ticket_url="https://example.com/tickets/1")

    sent = run_notifications(db_path, cinema.id, _config(tmp_path))

    assert sent == 1
    mock_send.assert_called_once()
    webhook_url, message = mock_send.call_args[0]
    assert "The Great Adventure" in message
    assert "2026-08-01" in message
    assert "18:00:00" in message
    assert "watchlist" in message
    assert "https://example.com/tickets/1" in message


@patch("cinema_recs.notify.send_notification")
def test_message_omits_ticket_link_when_absent(mock_send, db_path, cinema, tmp_path):
    _seed_recommended_movie(db_path, cinema, "No Ticket Movie", ticket_url=None)

    run_notifications(db_path, cinema.id, _config(tmp_path))

    message = mock_send.call_args[0][1]
    assert "Tickets:" not in message


@patch("cinema_recs.notify.send_notification")
def test_non_recommended_movie_never_notifies(mock_send, db_path, cinema, tmp_path):
    storage.upsert_showtime(
        db_path, cinema.id, "Ordinary Movie", date(2026, 8, 1), time(18, 0), None,
        datetime(2026, 8, 1, 10, 0, 0),
    )
    storage.upsert_movie_metadata(db_path, "Ordinary Movie", match_status="matched", tmdb_id=99)
    storage.upsert_movie_recommendation(db_path, "Ordinary Movie", is_recommended=False, reasons=None)

    sent = run_notifications(db_path, cinema.id, _config(tmp_path))

    assert sent == 0
    mock_send.assert_not_called()


@patch("cinema_recs.notify.send_notification")
def test_no_webhook_url_sends_nothing_without_calls(mock_send, db_path, cinema, tmp_path):
    _seed_recommended_movie(db_path, cinema, "The Great Adventure")

    sent = run_notifications(db_path, cinema.id, _config(tmp_path, webhook_url=None))

    assert sent == 0
    mock_send.assert_not_called()


@patch("cinema_recs.notify.send_notification")
def test_notifications_disabled_sends_nothing_without_calls(mock_send, db_path, cinema, tmp_path):
    _seed_recommended_movie(db_path, cinema, "The Great Adventure")

    sent = run_notifications(db_path, cinema.id, _config(tmp_path, enabled=False))

    assert sent == 0
    mock_send.assert_not_called()


@patch("cinema_recs.notify.send_notification")
def test_movie_that_stays_recommended_is_notified_only_once(mock_send, db_path, cinema, tmp_path):
    _seed_recommended_movie(db_path, cinema, "The Great Adventure")
    config = _config(tmp_path)

    first = run_notifications(db_path, cinema.id, config)
    second = run_notifications(db_path, cinema.id, config)

    assert first == 1
    assert second == 0
    assert mock_send.call_count == 1


@patch("cinema_recs.notify.send_notification")
def test_failed_delivery_leaves_movie_eligible_for_retry(mock_send, db_path, cinema, tmp_path):
    mock_send.side_effect = [Exception("webhook unreachable"), None]
    _seed_recommended_movie(db_path, cinema, "The Great Adventure")
    config = _config(tmp_path)

    first = run_notifications(db_path, cinema.id, config)
    second = run_notifications(db_path, cinema.id, config)

    assert first == 0
    assert second == 1
    assert mock_send.call_count == 2

    record = storage.get_notification_record(db_path, "The Great Adventure")
    assert record.active is True
    assert record.last_delivery_outcome == "sent"


@patch("cinema_recs.notify.send_notification")
def test_recommended_then_not_then_recommended_notifies_again(mock_send, db_path, cinema, tmp_path):
    _seed_recommended_movie(db_path, cinema, "The Great Adventure")
    config = _config(tmp_path)

    run_notifications(db_path, cinema.id, config)
    assert mock_send.call_count == 1

    storage.upsert_movie_recommendation(db_path, "The Great Adventure", is_recommended=False, reasons=None)
    run_notifications(db_path, cinema.id, config)
    assert mock_send.call_count == 1  # no notification for becoming unrecommended

    storage.upsert_movie_recommendation(db_path, "The Great Adventure", is_recommended=True, reasons="rating")
    run_notifications(db_path, cinema.id, config)
    assert mock_send.call_count == 2


@patch("cinema_recs.notify.send_notification")
def test_no_active_showtime_skips_without_error(mock_send, db_path, cinema, tmp_path):
    storage.upsert_movie_metadata(db_path, "Ghost Movie", match_status="matched", tmdb_id=1)
    storage.upsert_movie_recommendation(db_path, "Ghost Movie", is_recommended=True, reasons="watchlist")

    sent = run_notifications(db_path, cinema.id, _config(tmp_path))

    assert sent == 0
    mock_send.assert_not_called()
