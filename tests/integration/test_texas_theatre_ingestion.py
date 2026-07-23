from datetime import date, time, timedelta

import pytest

from cinema_recs import storage
from cinema_recs.ingest import run_ingestion
from cinema_recs.scraper import ScrapedShowtime, ScrapeResult


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_texas_theatre.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def texas_cinema(db_path):
    return storage.ensure_texas_theatre_cinema(db_path)


def test_texas_theatre_ingestion_end_to_end(db_path, texas_cinema, monkeypatch):
    mock_showtimes = [
        ScrapedShowtime(
            movie_title="BLOOD SIMPLE (35mm)",
            show_date=date(2026, 8, 10),
            start_time=time(19, 0),
            format="35mm",
            ticket_url="https://thetexastheatre.com/event/blood-simple-35mm/",
        ),
        ScrapedShowtime(
            movie_title="PARIS, TEXAS",
            show_date=date(2026, 8, 11),
            start_time=time(21, 30),
            format="4K",
            ticket_url="https://thetexastheatre.com/event/paris-texas-4k/",
        ),
    ]

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_texas_theatre_showtimes",
        lambda url: ScrapeResult(showtimes=mock_showtimes, reported_count=2),
    )

    run = run_ingestion(db_path, texas_cinema)

    assert run.outcome == "success"
    assert run.showtimes_captured == 2

    stored = storage.list_active_showtimes(db_path, texas_cinema.id)
    assert len(stored) == 2
    assert stored[0].movie_title == "BLOOD SIMPLE (35mm)"
    assert stored[0].format == "35mm"
    assert stored[0].ticket_url == "https://thetexastheatre.com/event/blood-simple-35mm/"


def test_texas_theatre_ingestion_stale_reconciliation(db_path, texas_cinema, monkeypatch):
    first_run = [
        ScrapedShowtime(
            movie_title="MOVIE A",
            show_date=date(2026, 8, 12),
            start_time=time(18, 0),
            format="35mm",
            ticket_url="https://thetexastheatre.com/event/movie-a/",
        ),
        ScrapedShowtime(
            movie_title="MOVIE B",
            show_date=date(2026, 8, 12),
            start_time=time(20, 30),
            format=None,
            ticket_url="https://thetexastheatre.com/event/movie-b/",
        ),
    ]
    second_run = [
        ScrapedShowtime(
            movie_title="MOVIE A",
            show_date=date(2026, 8, 12),
            start_time=time(18, 0),
            format="35mm",
            ticket_url="https://thetexastheatre.com/event/movie-a/",
        ),
    ]

    calls = iter([
        ScrapeResult(showtimes=first_run, reported_count=2),
        ScrapeResult(showtimes=second_run, reported_count=1),
    ])

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_texas_theatre_showtimes",
        lambda url: next(calls),
    )

    run_ingestion(db_path, texas_cinema)
    assert len(storage.list_active_showtimes(db_path, texas_cinema.id)) == 2

    run_ingestion(db_path, texas_cinema)
    active = storage.list_active_showtimes(db_path, texas_cinema.id)
    assert len(active) == 1
    assert active[0].movie_title == "MOVIE A"


def test_texas_theatre_full_window_ingestion_captures_dates_beyond_current_month(
    db_path, texas_cinema, monkeypatch
):
    # Simulates what a completed month-walk (scraper.py's
    # `_walk_texas_theatre_months`) would hand back in one run: showtimes
    # from this month and two months out, not just "this calendar month."
    this_month = date(2026, 8, 10)
    two_months_out = date(2026, 10, 5)
    showtimes = [
        ScrapedShowtime(
            movie_title="MOVIE A",
            show_date=this_month,
            start_time=time(19, 0),
            format="35mm",
            ticket_url="https://thetexastheatre.com/event/movie-a/",
        ),
        ScrapedShowtime(
            movie_title="MOVIE D",
            show_date=two_months_out,
            start_time=time(20, 0),
            format=None,
            ticket_url="https://thetexastheatre.com/event/movie-d/",
        ),
    ]
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_texas_theatre_showtimes",
        lambda url: ScrapeResult(showtimes=showtimes, reported_count=2, complete=True),
    )

    run = run_ingestion(db_path, texas_cinema)

    assert run.outcome == "success"
    active_dates = {s.show_date for s in storage.list_active_showtimes(db_path, texas_cinema.id)}
    assert active_dates == {this_month, two_months_out}
    assert two_months_out - this_month > timedelta(days=30)
