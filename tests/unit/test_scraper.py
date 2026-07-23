from datetime import date, timedelta

from cinema_recs.scraper import _walk_cinepolis_dates, looks_blocked, parse_showings_response

# Trimmed/representative excerpt of the real `showingsForDate` GraphQL
# response schema observed against the live Cinepolis McKinney API.
SAMPLE_RESPONSE = {
    "data": [
        {
            "id": "1645312",
            "time": "2026-07-23T15:00:00Z",
            "screenId": "1005",
            "movie": {"id": "40256", "name": "Toy Story 5"},
        },
        {
            "id": "1645315",
            "time": "2026-07-23T20:35:00Z",
            "screenId": "1007",
            "movie": {"id": "40225", "name": "Minions & Monsters"},
        },
    ],
    "count": 2,
}


def test_parse_showings_response_extracts_all_showtimes():
    showtimes = parse_showings_response(SAMPLE_RESPONSE)

    assert len(showtimes) == 2
    assert showtimes[0].movie_title == "Toy Story 5"
    assert showtimes[0].show_date == date(2026, 7, 23)
    # 2026-07-23T15:00:00Z is 10:00 AM Central (CDT, UTC-5)
    assert showtimes[0].start_time.hour == 10
    assert showtimes[0].start_time.minute == 0


def test_parse_showings_response_format_is_none():
    # The showingsForDate query has no format/auditorium label field.
    showtimes = parse_showings_response(SAMPLE_RESPONSE)
    assert all(s.format is None for s in showtimes)


def test_parse_showings_response_constructs_ticket_url_from_id():
    showtimes = parse_showings_response(SAMPLE_RESPONSE)

    assert showtimes[0].ticket_url == "https://www.cinepolisusa.com/mckinney/checkout/seats/1645312"
    assert showtimes[1].ticket_url == "https://www.cinepolisusa.com/mckinney/checkout/seats/1645315"


def test_parse_showings_response_ticket_url_is_none_without_id():
    response = {
        "data": [
            {
                "time": "2026-07-23T15:00:00Z",
                "screenId": "1005",
                "movie": {"id": "40256", "name": "Toy Story 5"},
            },
        ],
        "count": 1,
    }

    showtimes = parse_showings_response(response)

    assert showtimes[0].ticket_url is None


def test_parse_showings_response_skips_entries_without_movie_name():
    response = {
        "data": [
            {
                "id": "1",
                "time": "2026-07-23T15:00:00Z",
                "screenId": "1",
                "movie": {"id": "1", "name": ""},
            },
        ],
        "count": 1,
    }
    assert parse_showings_response(response) == []


def test_parse_showings_response_skips_unparseable_time():
    response = {
        "data": [
            {
                "id": "1",
                "time": "not-a-time",
                "screenId": "1",
                "movie": {"id": "1", "name": "Broken Movie"},
            },
        ],
        "count": 1,
    }
    assert parse_showings_response(response) == []


def test_parse_showings_response_returns_empty_list_for_no_data():
    assert parse_showings_response({"data": [], "count": 0}) == []


def test_looks_blocked_detects_cloudflare_interstitial():
    blocked_html = (
        "<title>Attention Required! | Cloudflare</title>"
        "<h1>Sorry, you have been blocked</h1>"
    )
    assert looks_blocked(blocked_html) is True


def test_looks_blocked_false_for_normal_page():
    assert looks_blocked("<html><body>The Great Adventure - 6:30 PM</body></html>") is False


# --- Full showtime window (feature 009): Cinepolis date-loop walking ---

START = date(2026, 7, 23)


def _response(entries, count=None):
    return {"data": entries, "count": count if count is not None else len(entries)}


def _entry(movie_title="Toy Story 5", showing_id="1"):
    return {
        "id": showing_id,
        "time": "2026-07-23T15:00:00Z",
        "screenId": "1005",
        "movie": {"id": "40256", "name": movie_title},
    }


def test_walk_cinepolis_dates_stops_after_two_consecutive_empty_dates():
    # today: 1 showing, next day: empty, day after: empty -> stop (complete)
    responses = {
        START: _response([_entry()]),
        START + timedelta(days=1): _response([]),
        START + timedelta(days=2): _response([]),
    }
    queried = []

    def query_date_fn(d):
        queried.append(d)
        return responses[d]

    result = _walk_cinepolis_dates(query_date_fn, START)

    assert queried == [START, START + timedelta(days=1), START + timedelta(days=2)]
    assert len(result.showtimes) == 1
    assert result.reported_count == 1
    assert result.complete is True
    assert result.incomplete_reason is None


def test_walk_cinepolis_dates_tolerates_single_empty_date():
    # A single dark day between two showing days must not stop the walk.
    responses = {
        START: _response([_entry("Movie A")]),
        START + timedelta(days=1): _response([]),
        START + timedelta(days=2): _response([_entry("Movie B")]),
        START + timedelta(days=3): _response([]),
        START + timedelta(days=4): _response([]),
    }

    def query_date_fn(d):
        return responses[d]

    result = _walk_cinepolis_dates(query_date_fn, START)

    assert {s.movie_title for s in result.showtimes} == {"Movie A", "Movie B"}
    assert result.complete is True


def test_walk_cinepolis_dates_marks_incomplete_when_a_date_fails():
    responses = {
        START: _response([_entry("Movie A")]),
        START + timedelta(days=1): _response([_entry("Movie B")]),
    }

    def query_date_fn(d):
        if d not in responses:
            raise RuntimeError("GraphQL request failed with HTTP 500")
        return responses[d]

    result = _walk_cinepolis_dates(query_date_fn, START)

    assert {s.movie_title for s in result.showtimes} == {"Movie A", "Movie B"}
    assert result.complete is False
    assert result.incomplete_reason is not None
    assert (START + timedelta(days=2)).isoformat() in result.incomplete_reason
