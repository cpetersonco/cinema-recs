from datetime import date, time

import pytest

from cinema_recs import storage
from cinema_recs.ingest import run_ingestion
from cinema_recs.scraper import ScrapedShowtime, ScrapeResult


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_angelika_dallas.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def angelika_cinema(db_path):
    return storage.ensure_angelika_dallas_cinema(db_path)


def test_angelika_dallas_ingestion_end_to_end(db_path, angelika_cinema, monkeypatch):
    mock_showtimes = [
        ScrapedShowtime(
            movie_title="THE ODYSSEY IN 70MM",
            show_date=date(2026, 8, 10),
            start_time=time(9, 0),
            format="70mm",
            ticket_url="https://angelikafilmcenter.com/cinemas/0000000009/sessions/94651/2523",
        ),
        ScrapedShowtime(
            movie_title="A QUIET INDIE FILM",
            show_date=date(2026, 8, 11),
            start_time=time(19, 30),
            format="Standard",
            ticket_url="https://angelikafilmcenter.com/cinemas/0000000009/sessions/94900/3010",
        ),
    ]

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_angelika_dallas_showtimes",
        lambda url: ScrapeResult(showtimes=mock_showtimes, reported_count=2),
    )

    run = run_ingestion(db_path, angelika_cinema)

    assert run.outcome == "success"
    assert run.showtimes_captured == 2

    stored = storage.list_active_showtimes(db_path, angelika_cinema.id)
    assert len(stored) == 2
    assert stored[0].movie_title == "THE ODYSSEY IN 70MM"
    assert stored[0].format == "70mm"
    assert stored[0].ticket_url == (
        "https://angelikafilmcenter.com/cinemas/0000000009/sessions/94651/2523"
    )


def test_angelika_dallas_ingestion_stale_reconciliation(db_path, angelika_cinema, monkeypatch):
    first_run = [
        ScrapedShowtime(
            movie_title="MOVIE A",
            show_date=date(2026, 8, 12),
            start_time=time(18, 0),
            format="Standard",
            ticket_url="https://angelikafilmcenter.com/cinemas/0000000009/sessions/1/1",
        ),
        ScrapedShowtime(
            movie_title="MOVIE B",
            show_date=date(2026, 8, 12),
            start_time=time(20, 30),
            format=None,
            ticket_url="https://angelikafilmcenter.com/cinemas/0000000009/sessions/2/2",
        ),
    ]
    second_run = [
        ScrapedShowtime(
            movie_title="MOVIE A",
            show_date=date(2026, 8, 12),
            start_time=time(18, 0),
            format="Standard",
            ticket_url="https://angelikafilmcenter.com/cinemas/0000000009/sessions/1/1",
        ),
    ]

    calls = iter([
        ScrapeResult(showtimes=first_run, reported_count=2),
        ScrapeResult(showtimes=second_run, reported_count=1),
    ])

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_angelika_dallas_showtimes",
        lambda url: next(calls),
    )

    run_ingestion(db_path, angelika_cinema)
    assert len(storage.list_active_showtimes(db_path, angelika_cinema.id)) == 2

    run_ingestion(db_path, angelika_cinema)
    active = storage.list_active_showtimes(db_path, angelika_cinema.id)
    assert len(active) == 1
    assert active[0].movie_title == "MOVIE A"


def test_angelika_dallas_ingestion_records_failure_outcome(db_path, angelika_cinema, monkeypatch):
    def _raise(url):
        raise RuntimeError("Angelika Dallas films request failed with HTTP 403")

    monkeypatch.setattr("cinema_recs.ingest.scrape_angelika_dallas_showtimes", _raise)

    run = run_ingestion(db_path, angelika_cinema)

    assert run.outcome == "failure"
    assert run.showtimes_captured == 0
    assert "403" in run.error_message
