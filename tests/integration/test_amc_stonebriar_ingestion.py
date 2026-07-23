from datetime import date, time

import pytest

from cinema_recs import storage
from cinema_recs.ingest import run_ingestion
from cinema_recs.scraper import ScrapedShowtime, ScrapeResult


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_amc_stonebriar.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def amc_stonebriar_cinema(db_path):
    return storage.ensure_amc_stonebriar_cinema(db_path)


def test_amc_stonebriar_ingestion_end_to_end(db_path, amc_stonebriar_cinema, monkeypatch):
    mock_showtimes = [
        ScrapedShowtime(
            movie_title="Moana",
            show_date=date(2026, 7, 23),
            start_time=time(18, 15),
            format="Laser at AMC",
            ticket_url="https://www.amctheatres.com/showtimes/145327763/seats",
        ),
        ScrapedShowtime(
            movie_title="The Odyssey",
            show_date=date(2026, 7, 23),
            start_time=time(18, 0),
            format="IMAX with Laser at AMC",
            ticket_url="https://www.amctheatres.com/showtimes/143799404/seats",
        ),
    ]

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_amc_stonebriar_showtimes",
        lambda url: ScrapeResult(showtimes=mock_showtimes, reported_count=2),
    )

    run = run_ingestion(db_path, amc_stonebriar_cinema)

    assert run.outcome == "success"
    assert run.showtimes_captured == 2

    stored = storage.list_active_showtimes(db_path, amc_stonebriar_cinema.id)
    assert len(stored) == 2
    by_title = {s.movie_title: s for s in stored}
    assert by_title["Moana"].format == "Laser at AMC"
    assert by_title["Moana"].ticket_url == "https://www.amctheatres.com/showtimes/145327763/seats"


def test_amc_stonebriar_ingestion_stale_reconciliation(db_path, amc_stonebriar_cinema, monkeypatch):
    first_run = [
        ScrapedShowtime(
            movie_title="Moana",
            show_date=date(2026, 7, 24),
            start_time=time(18, 15),
            format="Laser at AMC",
            ticket_url="https://www.amctheatres.com/showtimes/1/seats",
        ),
        ScrapedShowtime(
            movie_title="The Odyssey",
            show_date=date(2026, 7, 24),
            start_time=time(20, 30),
            format=None,
            ticket_url="https://www.amctheatres.com/showtimes/2/seats",
        ),
    ]
    second_run = [
        ScrapedShowtime(
            movie_title="Moana",
            show_date=date(2026, 7, 24),
            start_time=time(18, 15),
            format="Laser at AMC",
            ticket_url="https://www.amctheatres.com/showtimes/1/seats",
        ),
    ]

    calls = iter([
        ScrapeResult(showtimes=first_run, reported_count=2),
        ScrapeResult(showtimes=second_run, reported_count=1),
    ])

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_amc_stonebriar_showtimes",
        lambda url: next(calls),
    )

    run_ingestion(db_path, amc_stonebriar_cinema)
    assert len(storage.list_active_showtimes(db_path, amc_stonebriar_cinema.id)) == 2

    run_ingestion(db_path, amc_stonebriar_cinema)
    active = storage.list_active_showtimes(db_path, amc_stonebriar_cinema.id)
    assert len(active) == 1
    assert active[0].movie_title == "Moana"


def test_amc_stonebriar_ingestion_records_failure_outcome(db_path, amc_stonebriar_cinema, monkeypatch):
    def _raise(url):
        raise RuntimeError(
            "Redirected to AMC's bot/queue gate instead of the showtimes page"
        )

    monkeypatch.setattr("cinema_recs.ingest.scrape_amc_stonebriar_showtimes", _raise)

    run = run_ingestion(db_path, amc_stonebriar_cinema)

    assert run.outcome == "failure"
    assert run.showtimes_captured == 0
    assert "queue gate" in run.error_message


def test_amc_stonebriar_ingestion_partial_outcome_when_walk_incomplete(
    db_path, amc_stonebriar_cinema, monkeypatch
):
    mock_showtimes = [
        ScrapedShowtime(
            movie_title="Moana",
            show_date=date(2026, 7, 23),
            start_time=time(18, 15),
            format="Laser at AMC",
            ticket_url="https://www.amctheatres.com/showtimes/1/seats",
        ),
    ]

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_amc_stonebriar_showtimes",
        lambda url: ScrapeResult(
            showtimes=mock_showtimes,
            reported_count=1,
            complete=False,
            incomplete_reason="failed fetching 2026-07-24: Blocked by bot protection",
        ),
    )

    run = run_ingestion(db_path, amc_stonebriar_cinema)

    assert run.outcome == "partial"
    assert run.showtimes_captured == 1
    assert "2026-07-24" in run.error_message

    # An incomplete run must not stale-mark showtimes in unreached dates.
    stored = storage.list_active_showtimes(db_path, amc_stonebriar_cinema.id)
    assert len(stored) == 1
