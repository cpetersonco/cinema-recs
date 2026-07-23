from datetime import date, datetime, time

import pytest

from cinema_recs import storage


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    storage.init_schema(path)
    return path


@pytest.fixture
def cinema(db_path):
    return storage.get_or_create_cinema(
        db_path, "Cinepolis McKinney", "McKinney, TX (Hwy 121)", "https://example.com"
    )


def test_get_or_create_cinema_is_idempotent(db_path):
    first = storage.get_or_create_cinema(db_path, "Cinepolis McKinney", "McKinney, TX", "https://a")
    second = storage.get_or_create_cinema(db_path, "Cinepolis McKinney", "McKinney, TX", "https://b")

    assert first.id == second.id
    assert second.source_url == "https://b"


def test_upsert_showtime_inserts_new_record(db_path, cinema):
    seen_at = datetime(2026, 8, 1, 10, 0, 0)
    storage.upsert_showtime(
        db_path, cinema.id, "The Great Adventure", date(2026, 8, 1),
        time(18, 30), "Standard", seen_at,
    )

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].movie_title == "The Great Adventure"
    assert active[0].status == "active"


def test_upsert_showtime_persists_ticket_url(db_path, cinema):
    seen_at = datetime(2026, 8, 1, 10, 0, 0)
    storage.upsert_showtime(
        db_path, cinema.id, "The Great Adventure", date(2026, 8, 1),
        time(18, 30), "Standard", seen_at,
        ticket_url="https://www.cinepolisusa.com/mckinney/checkout/seats/12345",
    )

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert active[0].ticket_url == "https://www.cinepolisusa.com/mckinney/checkout/seats/12345"


def test_upsert_showtime_ticket_url_defaults_to_none(db_path, cinema):
    seen_at = datetime(2026, 8, 1, 10, 0, 0)
    storage.upsert_showtime(
        db_path, cinema.id, "The Great Adventure", date(2026, 8, 1),
        time(18, 30), "Standard", seen_at,
    )

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert active[0].ticket_url is None


def test_upsert_showtime_survives_stale_reactivation_with_ticket_url(db_path, cinema):
    t1 = datetime(2026, 8, 1, 10, 0, 0)
    t2 = datetime(2026, 8, 2, 10, 0, 0)
    t3 = datetime(2026, 8, 3, 10, 0, 0)

    storage.upsert_showtime(
        db_path, cinema.id, "Movie", date(2026, 8, 1), time(18, 30), None, t1,
        ticket_url="https://www.cinepolisusa.com/mckinney/checkout/seats/1",
    )
    storage.mark_stale_showtimes(db_path, cinema.id, t2)
    storage.upsert_showtime(
        db_path, cinema.id, "Movie", date(2026, 8, 1), time(18, 30), None, t3,
        ticket_url="https://www.cinepolisusa.com/mckinney/checkout/seats/1",
    )

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].ticket_url == "https://www.cinepolisusa.com/mckinney/checkout/seats/1"


def test_upsert_showtime_does_not_duplicate_on_rerun(db_path, cinema):
    seen_at_1 = datetime(2026, 8, 1, 10, 0, 0)
    seen_at_2 = datetime(2026, 8, 1, 13, 0, 0)

    for seen_at in (seen_at_1, seen_at_2):
        storage.upsert_showtime(
            db_path, cinema.id, "The Great Adventure", date(2026, 8, 1),
            time(18, 30), "Standard", seen_at,
        )

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].last_seen_at == seen_at_2


def test_mark_stale_showtimes_excludes_freshly_seen(db_path, cinema):
    old_seen_at = datetime(2026, 8, 1, 10, 0, 0)
    new_seen_at = datetime(2026, 8, 1, 13, 0, 0)

    storage.upsert_showtime(
        db_path, cinema.id, "Old Movie", date(2026, 8, 1), time(18, 30), None, old_seen_at
    )
    storage.upsert_showtime(
        db_path, cinema.id, "New Movie", date(2026, 8, 1), time(20, 0), None, new_seen_at
    )

    affected = storage.mark_stale_showtimes(db_path, cinema.id, new_seen_at)

    assert affected == 1
    active = storage.list_active_showtimes(db_path, cinema.id)
    assert [s.movie_title for s in active] == ["New Movie"]


def test_reappearing_showtime_reactivates_instead_of_duplicating(db_path, cinema):
    t1 = datetime(2026, 8, 1, 10, 0, 0)
    t2 = datetime(2026, 8, 2, 10, 0, 0)
    t3 = datetime(2026, 8, 3, 10, 0, 0)

    storage.upsert_showtime(db_path, cinema.id, "Movie", date(2026, 8, 1), time(18, 30), None, t1)
    storage.mark_stale_showtimes(db_path, cinema.id, t2)  # not re-seen at t2 -> stale
    storage.upsert_showtime(db_path, cinema.id, "Movie", date(2026, 8, 1), time(18, 30), None, t3)

    active = storage.list_active_showtimes(db_path, cinema.id)
    assert len(active) == 1
    assert active[0].status == "active"
