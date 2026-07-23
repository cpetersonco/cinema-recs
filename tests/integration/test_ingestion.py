from datetime import date, time, timedelta

import pytest

from cinema_recs import storage
from cinema_recs.ingest import run_ingestion
from cinema_recs.scraper import ScrapedShowtime, ScrapeResult


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_ingestion.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def cinema(db_path):
    return storage.get_or_create_cinema(
        db_path, "Cinepolis McKinney", "McKinney, TX", "https://example.com"
    )


def test_cinepolis_full_window_ingestion_captures_dates_beyond_tomorrow(
    db_path, cinema, monkeypatch
):
    # Simulates what a completed multi-date walk (scraper.py's
    # `_walk_cinepolis_dates`) would hand back in one run: showtimes
    # spanning today, next week, and next month, not just "today."
    today = date(2026, 7, 23)
    showtimes = [
        ScrapedShowtime("Movie A", today, time(19, 0), None, None),
        ScrapedShowtime("Movie B", today + timedelta(days=7), time(20, 0), None, None),
        ScrapedShowtime("Movie C", today + timedelta(days=35), time(18, 30), None, None),
    ]
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(showtimes=showtimes, reported_count=3, complete=True),
    )

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "success"
    assert run.showtimes_captured == 3

    active = storage.list_active_showtimes(db_path, cinema.id)
    active_dates = {s.show_date for s in active}
    assert active_dates == {today, today + timedelta(days=7), today + timedelta(days=35)}


def test_cinepolis_incomplete_walk_does_not_stale_mark_unfetched_showtimes(
    db_path, cinema, monkeypatch
):
    today = date(2026, 7, 23)
    far_out = ScrapedShowtime("Movie Far Out", today + timedelta(days=21), time(18, 0), None, None)

    # First run: a complete walk captures a showtime 3 weeks out.
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(showtimes=[far_out], reported_count=1, complete=True),
    )
    run_ingestion(db_path, cinema)
    assert len(storage.list_active_showtimes(db_path, cinema.id)) == 1

    # Second run: the walk fails partway through (e.g. a later date's
    # fetch raised after retries) before ever reaching the far-out
    # showtime's date again - it must NOT be treated as gone.
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(
            showtimes=[], reported_count=0, complete=False,
            incomplete_reason="failed fetching 2026-07-24: HTTP 500",
        ),
    )
    run = run_ingestion(db_path, cinema)

    assert run.outcome == "failure"
    assert "2026-07-24" in run.error_message  # names the failed date (Constitution V)
    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].movie_title == "Movie Far Out"
    assert active[0].status == "active"


def test_cinepolis_partial_walk_recorded_as_partial_with_captured_showtimes(
    db_path, cinema, monkeypatch
):
    # A walk that captures some dates before failing partway through is
    # "partial" (some real data came through), not a bare "failure" -
    # still gated from stale-marking either way.
    today = date(2026, 7, 23)
    partial_showtimes = [ScrapedShowtime("Movie A", today, time(19, 0), None, None)]
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes",
        lambda url: ScrapeResult(
            showtimes=partial_showtimes, reported_count=1, complete=False,
            incomplete_reason="failed fetching 2026-07-24: HTTP 500",
        ),
    )

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "partial"
    assert run.showtimes_captured == 1
    assert "2026-07-24" in run.error_message
    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].movie_title == "Movie A"
