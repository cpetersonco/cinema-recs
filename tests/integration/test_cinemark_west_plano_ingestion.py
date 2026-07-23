from datetime import date, time

import pytest

from cinema_recs import storage
from cinema_recs.ingest import run_ingestion
from cinema_recs.scraper import ScrapedShowtime, ScrapeResult


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test_cinemark_west_plano.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def cinemark_cinema(db_path):
    return storage.ensure_cinemark_west_plano_cinema(db_path)


def test_cinemark_west_plano_ingestion_end_to_end(db_path, cinemark_cinema, monkeypatch):
    mock_showtimes = [
        ScrapedShowtime(
            movie_title="The Odyssey",
            show_date=date(2026, 7, 24),
            start_time=time(10, 50),
            format="70mm",
            ticket_url="https://www.cinemark.com/TicketSeatMap/?TheaterId=231&ShowtimeId=865306",
        ),
        ScrapedShowtime(
            movie_title="The Odyssey",
            show_date=date(2026, 7, 24),
            start_time=time(8, 0),
            format="XD+D-BOX",
            ticket_url="https://www.cinemark.com/TicketSeatMap/?TheaterId=231&ShowtimeId=865297",
        ),
    ]

    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_cinemark_west_plano_showtimes",
        lambda url: ScrapeResult(showtimes=mock_showtimes, reported_count=2),
    )

    run = run_ingestion(db_path, cinemark_cinema)

    assert run.outcome == "success"
    assert run.showtimes_captured == 2

    stored = storage.list_active_showtimes(db_path, cinemark_cinema.id)
    assert len(stored) == 2
    formats = {s.format for s in stored}
    assert formats == {"70mm", "XD+D-BOX"}
    seventymm = next(s for s in stored if s.format == "70mm")
    assert seventymm.movie_title == "The Odyssey"


def test_cinemark_west_plano_ingestion_stale_reconciliation(db_path, cinemark_cinema, monkeypatch):
    first_run = [
        ScrapedShowtime(
            movie_title="Movie A",
            show_date=date(2026, 8, 1),
            start_time=time(18, 0),
            format="Standard",
            ticket_url="https://www.cinemark.com/TicketSeatMap/?TheaterId=231&ShowtimeId=1",
        ),
        ScrapedShowtime(
            movie_title="Movie B",
            show_date=date(2026, 8, 1),
            start_time=time(20, 30),
            format=None,
            ticket_url="https://www.cinemark.com/TicketSeatMap/?TheaterId=231&ShowtimeId=2",
        ),
    ]
    second_run = [first_run[0]]

    calls = iter([
        ScrapeResult(showtimes=first_run, reported_count=2),
        ScrapeResult(showtimes=second_run, reported_count=1),
    ])
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_cinemark_west_plano_showtimes",
        lambda url: next(calls),
    )

    run_ingestion(db_path, cinemark_cinema)
    assert len(storage.list_active_showtimes(db_path, cinemark_cinema.id)) == 2

    run_ingestion(db_path, cinemark_cinema)
    active = storage.list_active_showtimes(db_path, cinemark_cinema.id)
    assert len(active) == 1
    assert active[0].movie_title == "Movie A"


def test_cinemark_west_plano_ingestion_partial_outcome_on_incomplete_walk(
    db_path, cinemark_cinema, monkeypatch
):
    showtime = ScrapedShowtime(
        movie_title="Movie A",
        show_date=date(2026, 8, 1),
        start_time=time(18, 0),
        format="Standard",
        ticket_url="https://www.cinemark.com/TicketSeatMap/?TheaterId=231&ShowtimeId=1",
    )
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_cinemark_west_plano_showtimes",
        lambda url: ScrapeResult(
            showtimes=[showtime],
            reported_count=1,
            complete=False,
            incomplete_reason="failed fetching 2026-08-02: boom",
        ),
    )

    run = run_ingestion(db_path, cinemark_cinema)

    assert run.outcome == "partial"
    assert run.showtimes_captured == 1
    assert "2026-08-02" in run.error_message


def test_cinemark_west_plano_ingestion_records_failure_outcome(
    db_path, cinemark_cinema, monkeypatch
):
    def _raise(url):
        raise RuntimeError("Cinemark West Plano fetch failed with HTTP 500")

    monkeypatch.setattr("cinema_recs.ingest.scrape_cinemark_west_plano_showtimes", _raise)

    run = run_ingestion(db_path, cinemark_cinema)

    assert run.outcome == "failure"
    assert run.showtimes_captured == 0
    assert "500" in run.error_message
