from datetime import date, time

import pytest

from cinema_recs import storage
from cinema_recs.ingest import run_ingestion
from cinema_recs.scraper import ScrapedShowtime


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


def test_run_ingestion_reconciles_removed_showtime(db_path, cinema, monkeypatch):
    first_run_showtimes = [
        ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard"),
        ScrapedShowtime("Movie B", date(2026, 8, 1), time(20, 0), None),
    ]
    second_run_showtimes = [
        ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard"),
    ]

    calls = iter([first_run_showtimes, second_run_showtimes])
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes", lambda url: next(calls)
    )

    run_ingestion(db_path, cinema)
    active_after_first = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active_after_first) == 2

    run_ingestion(db_path, cinema)
    active_after_second = storage.list_active_showtimes(db_path, cinema.id)
    assert [s.movie_title for s in active_after_second] == ["Movie A"]


def test_run_ingestion_reactivates_reappearing_showtime(db_path, cinema, monkeypatch):
    showtime = ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard")
    calls = iter([[showtime], [], [showtime]])
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes", lambda url: next(calls)
    )

    run_ingestion(db_path, cinema)
    run_ingestion(db_path, cinema)  # showtime disappears -> stale
    assert storage.list_active_showtimes(db_path, cinema.id) == []

    run_ingestion(db_path, cinema)  # showtime reappears -> active again, no duplicate
    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].status == "active"


def test_run_ingestion_records_failure_on_scrape_error(db_path, cinema, monkeypatch):
    def raise_error(url):
        raise RuntimeError("source unreachable")

    monkeypatch.setattr("cinema_recs.ingest.scrape_showtimes", raise_error)

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "failure"
    assert run.showtimes_captured == 0
    assert "source unreachable" in run.error_message


def test_run_ingestion_distinguishes_zero_found_from_failure(db_path, cinema, monkeypatch):
    monkeypatch.setattr("cinema_recs.ingest.scrape_showtimes", lambda url: [])

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "success"
    assert run.showtimes_captured == 0
