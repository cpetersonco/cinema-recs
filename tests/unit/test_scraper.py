from datetime import date

from cinema_recs.scraper import looks_blocked, parse_showings_response

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
