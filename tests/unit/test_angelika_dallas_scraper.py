from datetime import date, time

from cinema_recs.scraper import (
    _parse_angelika_date_strip_label,
    _parse_angelika_datetime,
    _walk_angelika_dallas_dates,
    parse_angelika_dallas_films,
)

# Fixture shape mirrors the real production-api.readingcinemas.com /films
# response for the Angelika Dallas cinemaId (0000000009), confirmed via live
# network inspection during feature 008 planning (see research.md §1):
# nowShowing.data.movies[].showdates[].showtypes[].showtimes[].
SAMPLE_FILMS_PAYLOAD = {
    "nowShowing": {
        "statusCode": 0,
        "data": {
            "movies": [
                {
                    "name": "THE ODYSSEY IN 70MM",
                    "slug": "2523",
                    "movieSlug": "the-odyssey-in-70mm",
                    "showdates": [
                        {
                            "date": "2026-07-23",
                            "showtypes": [
                                {
                                    "type": "70mm",
                                    "subType": "",
                                    "showtimes": [
                                        {
                                            "id": "94651",
                                            "ScheduledFilmId": "HO00008448",
                                            "date_time": "2026-07-23T09:00:00-05",
                                            "soldout": False,
                                        },
                                        {
                                            "id": "94535",
                                            "ScheduledFilmId": "HO00008448",
                                            "date_time": "2026-07-23T12:25:00-05",
                                            "soldout": False,
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                },
                {
                    "name": "A QUIET INDIE FILM",
                    "slug": "3010",
                    "showdates": [
                        {
                            "date": "2026-07-24",
                            "showtypes": [
                                {
                                    "type": "Standard",
                                    "showtimes": [
                                        {
                                            "id": "94900",
                                            "date_time": "2026-07-24T19:30:00-05",
                                            "soldout": False,
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
            ],
            "filter": {},
        },
    }
}

SAMPLE_PAYLOAD_WITH_MISSING_FIELDS = {
    "nowShowing": {
        "data": {
            "movies": [
                {
                    "name": "",
                    "slug": "4000",
                    "showdates": [
                        {
                            "date": "2026-07-25",
                            "showtypes": [
                                {
                                    "type": "Standard",
                                    "showtimes": [
                                        {"id": "95000", "date_time": "2026-07-25T18:00:00-05"}
                                    ],
                                }
                            ],
                        }
                    ],
                },
                {
                    "name": "MISSING TIME FILM",
                    "slug": "4001",
                    "showdates": [
                        {
                            "date": "2026-07-25",
                            "showtypes": [
                                {
                                    "type": "Standard",
                                    "showtimes": [{"id": "95001", "date_time": "not-a-date"}],
                                }
                            ],
                        }
                    ],
                },
            ]
        }
    }
}


def test_parse_angelika_datetime_normalizes_offset_without_minutes():
    parsed = _parse_angelika_datetime("2026-07-23T09:00:00-05")
    assert parsed is not None
    assert parsed.date() == date(2026, 7, 23)
    assert parsed.time() == time(9, 0)


def test_parse_angelika_datetime_rejects_garbage():
    assert _parse_angelika_datetime("not-a-date") is None


def test_parse_angelika_dallas_films_extracts_showtimes_across_movies():
    showtimes, reported_count = parse_angelika_dallas_films(SAMPLE_FILMS_PAYLOAD)

    assert reported_count == 3
    assert len(showtimes) == 3

    sh0 = showtimes[0]
    assert sh0.movie_title == "THE ODYSSEY IN 70MM"
    assert sh0.show_date == date(2026, 7, 23)
    assert sh0.start_time == time(9, 0)
    assert sh0.format == "70mm"
    assert sh0.ticket_url == (
        "https://angelikafilmcenter.com/cinemas/0000000009/sessions/94651/2523"
    )

    sh2 = showtimes[2]
    assert sh2.movie_title == "A QUIET INDIE FILM"
    assert sh2.format == "Standard"
    assert sh2.ticket_url == (
        "https://angelikafilmcenter.com/cinemas/0000000009/sessions/94900/3010"
    )


def test_parse_angelika_dallas_films_skips_missing_title_or_unparseable_time():
    showtimes, reported_count = parse_angelika_dallas_films(SAMPLE_PAYLOAD_WITH_MISSING_FIELDS)

    # Both sessions are reported (they exist in the source), but neither is
    # usable: one has an empty title, the other an unparseable date_time.
    assert reported_count == 2
    assert showtimes == []


# --- Full showtime window (feature 009): date-strip walk ---

TODAY = date(2026, 7, 23)


def test_parse_angelika_date_strip_label_handles_today_and_tomorrow():
    assert _parse_angelika_date_strip_label("Today, 7/23", TODAY) == date(2026, 7, 23)
    assert _parse_angelika_date_strip_label("Tomorrow, 7/24", TODAY) == date(2026, 7, 24)
    assert _parse_angelika_date_strip_label("Sunday 7/26", TODAY) == date(2026, 7, 26)


def test_parse_angelika_date_strip_label_rolls_over_new_year():
    # A label like "1/13" seen while today is in July belongs to next year.
    assert _parse_angelika_date_strip_label("Wednesday 1/13", TODAY) == date(2027, 1, 13)


def test_parse_angelika_date_strip_label_returns_none_for_unmatched_text():
    assert _parse_angelika_date_strip_label("MOVIES", TODAY) is None


def _payload_for_date(day: str, movie_title: str = "Movie") -> dict:
    return {
        "nowShowing": {
            "data": {
                "movies": [
                    {
                        "name": movie_title,
                        "slug": "1",
                        "showdates": [
                            {
                                "date": day,
                                "showtypes": [
                                    {
                                        "type": "Standard",
                                        "showtimes": [
                                            {"id": "1", "date_time": f"{day}T19:00:00-05"}
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        }
    }


def test_walk_angelika_dallas_dates_reuses_initial_payload_for_first_date():
    labeled_dates = [("Today, 7/23", TODAY), ("Tomorrow, 7/24", date(2026, 7, 24))]
    initial_payload = _payload_for_date("2026-07-23", "Movie A")
    queried = []

    def query_label_fn(label):
        queried.append(label)
        return _payload_for_date("2026-07-24", "Movie B")

    result = _walk_angelika_dallas_dates(labeled_dates, initial_payload, query_label_fn)

    # Only the second date is fetched via query_label_fn - the first reuses
    # the payload the page's own initial load already captured.
    assert queried == ["Tomorrow, 7/24"]
    assert {s.movie_title for s in result.showtimes} == {"Movie A", "Movie B"}
    assert result.complete is True
    assert result.incomplete_reason is None


def test_walk_angelika_dallas_dates_walks_every_labeled_date():
    labeled_dates = [
        ("Today, 7/23", TODAY),
        ("Tomorrow, 7/24", date(2026, 7, 24)),
        ("Saturday 7/25", date(2026, 7, 25)),
    ]
    initial_payload = _payload_for_date("2026-07-23", "Movie A")

    def query_label_fn(label):
        day = "2026-07-24" if "7/24" in label else "2026-07-25"
        return _payload_for_date(day, f"Movie for {label}")

    result = _walk_angelika_dallas_dates(labeled_dates, initial_payload, query_label_fn)

    assert len(result.showtimes) == 3
    assert result.complete is True


def test_walk_angelika_dallas_dates_marks_incomplete_when_a_date_fails():
    labeled_dates = [
        ("Today, 7/23", TODAY),
        ("Tomorrow, 7/24", date(2026, 7, 24)),
        ("Saturday 7/25", date(2026, 7, 25)),
    ]
    initial_payload = _payload_for_date("2026-07-23", "Movie A")

    def query_label_fn(label):
        if label == "Tomorrow, 7/24":
            raise RuntimeError("Angelika Dallas films request failed with HTTP 500")
        return _payload_for_date("2026-07-25", "Movie C")

    result = _walk_angelika_dallas_dates(labeled_dates, initial_payload, query_label_fn)

    # Stops at the failed date - never attempts "Saturday 7/25" after it.
    assert {s.movie_title for s in result.showtimes} == {"Movie A"}
    assert result.complete is False
    assert "Tomorrow, 7/24" in result.incomplete_reason


def test_walk_angelika_dallas_dates_no_labeled_dates_is_complete_and_empty():
    result = _walk_angelika_dallas_dates([], {}, lambda label: {})
    assert result.showtimes == []
    assert result.complete is True
