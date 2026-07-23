from unittest.mock import Mock, patch

import pytest
import requests

from cinema_recs.tmdb_client import (
    get_movie_details,
    match_title,
    search_movie,
    strip_event_suffix,
    strip_promo_price_prefix,
)


def _mock_response(json_data, status_ok=True):
    response = Mock()
    response.json.return_value = json_data
    if status_ok:
        response.raise_for_status.return_value = None
    else:
        response.raise_for_status.side_effect = requests.HTTPError("boom")
    return response


@patch("cinema_recs.tmdb_client.time.sleep")
@patch("cinema_recs.tmdb_client.requests.get")
def test_search_movie_parses_results(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(
        {
            "results": [
                {"id": 42, "title": "The Great Adventure", "popularity": 10.0,
                 "vote_count": 100, "release_date": "2024-05-01"},
            ]
        }
    )

    results = search_movie("key", "The Great Adventure")

    assert len(results) == 1
    assert results[0].tmdb_id == 42
    assert results[0].title == "The Great Adventure"
    assert results[0].release_year == 2024
    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["params"] == {"api_key": "key", "query": "The Great Adventure"}


@patch("cinema_recs.tmdb_client.time.sleep")
@patch("cinema_recs.tmdb_client.requests.get")
def test_get_movie_details_parses_fields(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(
        {
            "id": 42,
            "title": "The Great Adventure",
            "genres": [{"name": "Action"}, {"name": "Adventure"}],
            "overview": "A movie.",
            "release_date": "2024-05-01",
            "vote_average": 7.5,
            "runtime": 118,
            "poster_path": "/poster.jpg",
        }
    )

    details = get_movie_details("key", 42)

    assert details.tmdb_id == 42
    assert details.genres == ["Action", "Adventure"]
    assert details.release_year == 2024
    assert details.average_rating == 7.5
    assert details.runtime_minutes == 118
    assert details.poster_path == "/poster.jpg"


def _result(title, tmdb_id=1, vote_count=100):
    from cinema_recs.tmdb_client import TmdbSearchResult
    return TmdbSearchResult(tmdb_id=tmdb_id, title=title, popularity=1.0, vote_count=vote_count, release_year=2024)


def test_match_title_accepts_normalized_exact_match():
    results = [_result("The Great Adventure!", tmdb_id=42)]

    match = match_title("the great adventure", results)

    assert match.status == "matched"
    assert match.tmdb_id == 42


def test_match_title_strips_promo_price_prefix():
    results = [_result("The Mask", tmdb_id=1)]

    match = match_title("$5 The Mask", results)

    assert match.status == "matched"
    assert match.tmdb_id == 1


def test_match_title_returns_unmatched_when_no_results():
    match = match_title("Some Unknown Movie", [])

    assert match.status == "unmatched"


def test_match_title_returns_unmatched_when_no_close_title():
    results = [_result("A Completely Different Film", tmdb_id=99)]

    match = match_title("Some Unknown Movie", results)

    assert match.status == "unmatched"


def test_match_title_returns_ambiguous_for_close_duplicate_titles():
    results = [
        _result("The Great Adventure", tmdb_id=1, vote_count=100),
        _result("The Great Adventure", tmdb_id=2, vote_count=90),
    ]

    match = match_title("The Great Adventure", results)

    assert match.status == "ambiguous"
    assert match.tmdb_id is None


def test_match_title_accepts_clear_leader_among_duplicate_titles():
    results = [
        _result("The Great Adventure", tmdb_id=1, vote_count=1000),
        _result("The Great Adventure", tmdb_id=2, vote_count=10),
    ]

    match = match_title("The Great Adventure", results)

    assert match.status == "matched"
    assert match.tmdb_id == 1


@patch("cinema_recs.tmdb_client.time.sleep")
@patch("cinema_recs.tmdb_client.requests.get")
def test_search_movie_paces_requests_with_fixed_delay(mock_get, mock_sleep):
    mock_get.return_value = _mock_response({"results": []})

    search_movie("key", "Anything")

    mock_sleep.assert_called()


@patch("cinema_recs.tmdb_client.time.sleep")
@patch("cinema_recs.tmdb_client.requests.get")
def test_search_movie_retries_on_transient_failure_then_succeeds(mock_get, mock_sleep):
    failing_response = _mock_response({}, status_ok=False)
    ok_response = _mock_response({"results": []})
    mock_get.side_effect = [failing_response, ok_response]

    results = search_movie("key", "Anything")

    assert results == []
    assert mock_get.call_count == 2


@patch("cinema_recs.tmdb_client.time.sleep")
@patch("cinema_recs.tmdb_client.requests.get")
def test_search_movie_raises_after_exhausting_retries(mock_get, mock_sleep):
    mock_get.return_value = _mock_response({}, status_ok=False)

    with pytest.raises(requests.HTTPError):
        search_movie("key", "Anything")


def test_strip_promo_price_prefix_removes_dollar_amount():
    assert strip_promo_price_prefix("$5 The Mask") == "The Mask"
    assert strip_promo_price_prefix("$12.50 Some Movie") == "Some Movie"


def test_strip_promo_price_prefix_leaves_normal_titles_unchanged():
    assert strip_promo_price_prefix("The Mask") == "The Mask"


def test_strip_event_suffix_removes_plus_descriptor():
    assert strip_event_suffix("Midsommar + Costume Contest") == "Midsommar"
    assert strip_event_suffix("The Adventures of Prince Achmed + Live Score") == (
        "The Adventures of Prince Achmed"
    )


def test_strip_event_suffix_removes_trailing_parenthetical():
    assert (
        strip_event_suffix("The End of Evangelion (EVANGELION 30th Movie Fest)")
        == "The End of Evangelion"
    )


def test_strip_event_suffix_leaves_normal_titles_unchanged():
    assert strip_event_suffix("The Mask") == "The Mask"
    assert strip_event_suffix("2001: A Space Odyssey") == "2001: A Space Odyssey"
