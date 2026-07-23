from datetime import date, time

from cinema_recs.scraper import _parse_angelika_datetime, parse_angelika_dallas_films

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
