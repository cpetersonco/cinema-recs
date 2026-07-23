from datetime import date, time

import pytest

from cinema_recs import storage
from cinema_recs.ingest import run_ingestion
from cinema_recs.scraper import ScrapedShowtime, ScrapeResult


def _result(showtimes, reported_count=None):
    return ScrapeResult(
        showtimes=showtimes,
        reported_count=reported_count if reported_count is not None else len(showtimes),
    )


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
        ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard", "https://example.com/tickets/1"),
        ScrapedShowtime("Movie B", date(2026, 8, 1), time(20, 0), None, None),
    ]
    second_run_showtimes = [
        ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard", "https://example.com/tickets/1"),
    ]

    calls = iter([_result(first_run_showtimes), _result(second_run_showtimes)])
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
    showtime = ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard", "https://example.com/tickets/1")
    calls = iter([_result([showtime]), _result([]), _result([showtime])])
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


def test_run_ingestion_persists_ticket_url_from_scraped_showtime(db_path, cinema, monkeypatch):
    showtime = ScrapedShowtime(
        "Movie A", date(2026, 8, 1), time(18, 0), "Standard",
        "https://www.cinepolisusa.com/mckinney/checkout/seats/999",
    )
    monkeypatch.setattr("cinema_recs.ingest.scrape_showtimes", lambda url: _result([showtime]))

    run_ingestion(db_path, cinema)

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert active[0].ticket_url == "https://www.cinepolisusa.com/mckinney/checkout/seats/999"


def test_run_ingestion_records_failure_on_scrape_error(db_path, cinema, monkeypatch):
    def raise_error(url):
        raise RuntimeError("source unreachable")

    monkeypatch.setattr("cinema_recs.ingest.scrape_showtimes", raise_error)

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "failure"
    assert run.showtimes_captured == 0
    assert "source unreachable" in run.error_message


def test_run_ingestion_distinguishes_zero_found_from_failure(db_path, cinema, monkeypatch):
    monkeypatch.setattr("cinema_recs.ingest.scrape_showtimes", lambda url: _result([]))

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "success"
    assert run.showtimes_captured == 0


def test_run_ingestion_reports_partial_when_entries_are_skipped(db_path, cinema, monkeypatch):
    showtime = ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard", None)
    # The source's GraphQL response reported 3 showings, but only 1 survived
    # parsing (e.g. 2 had missing titles/unparseable times, per
    # parse_showings_response's skip logic) — a genuine partial result.
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes", lambda url: _result([showtime], reported_count=3)
    )

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "partial"
    assert run.showtimes_captured == 1
    assert "2 showing(s) skipped" in run.error_message


def test_run_ingestion_success_when_reported_count_matches(db_path, cinema, monkeypatch):
    showtime = ScrapedShowtime("Movie A", date(2026, 8, 1), time(18, 0), "Standard", None)
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_showtimes", lambda url: _result([showtime], reported_count=1)
    )

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "success"


# --- Explicit source_type dispatch (feature 011) ---

SCRAPER_NAMES = (
    "scrape_showtimes",
    "scrape_texas_theatre_showtimes",
    "scrape_angelika_dallas_showtimes",
)


def _refuse_if_called(name):
    def _fail(url):
        raise AssertionError(f"{name} should not have been called")
    return _fail


def _assert_dispatches_to(db_path, monkeypatch, source_type, expected_scraper_name):
    cinema = storage.get_or_create_cinema(
        db_path, "Any Name", "Anywhere", "https://example.com", source_type=source_type
    )
    called = []
    for name in SCRAPER_NAMES:
        if name == expected_scraper_name:
            monkeypatch.setattr(
                f"cinema_recs.ingest.{name}",
                lambda url, name=name: (called.append(name), _result([]))[1],
            )
        else:
            monkeypatch.setattr(f"cinema_recs.ingest.{name}", _refuse_if_called(name))

    run_ingestion(db_path, cinema)

    assert called == [expected_scraper_name]


def test_run_ingestion_dispatches_on_cinepolis_source_type(db_path, monkeypatch):
    _assert_dispatches_to(db_path, monkeypatch, "cinepolis", "scrape_showtimes")


def test_run_ingestion_dispatches_on_texas_theatre_source_type(db_path, monkeypatch):
    _assert_dispatches_to(db_path, monkeypatch, "texas_theatre", "scrape_texas_theatre_showtimes")


def test_run_ingestion_dispatches_on_angelika_dallas_source_type(db_path, monkeypatch):
    _assert_dispatches_to(
        db_path, monkeypatch, "angelika_dallas", "scrape_angelika_dallas_showtimes"
    )


def test_run_ingestion_fails_loudly_for_unrecognized_source_type(db_path, monkeypatch):
    cinema = storage.get_or_create_cinema(
        db_path, "Mystery Cinema", "Nowhere", "https://example.com", source_type="mystery_source"
    )
    for name in SCRAPER_NAMES:
        monkeypatch.setattr(f"cinema_recs.ingest.{name}", _refuse_if_called(name))

    run = run_ingestion(db_path, cinema)

    assert run.outcome == "failure"
    assert "mystery_source" in run.error_message
