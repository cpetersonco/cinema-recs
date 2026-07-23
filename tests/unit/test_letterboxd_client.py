from unittest.mock import Mock, patch

import pytest
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
from curl_cffi.requests.exceptions import HTTPError

from cinema_recs.letterboxd_client import (
    fetch_best_of_list_slugs,
    fetch_movie_rating,
    fetch_watchlist_slugs,
    resolve_letterboxd_slug,
)

LD_JSON_HTML = """
<script type="application/ld+json">
/* <![CDATA[ */
{"@type":"Movie","aggregateRating":{"@type":"AggregateRating","ratingValue":4.23,"bestRating":5,"worstRating":0.5}}
/* ]]> */
</script>
"""


def _mock_response(status_code=200, url="", text="", history=None):
    response = Mock()
    response.status_code = status_code
    response.ok = status_code < 400
    response.url = url
    response.text = text
    response.history = history or []
    return response


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_resolve_letterboxd_slug_follows_redirect(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(status_code=200, url="https://letterboxd.com/film/inception/")

    slug = resolve_letterboxd_slug(27205)

    assert slug == "inception"
    mock_get.assert_called_once_with("https://letterboxd.com/tmdb/27205/", timeout=10)


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_resolve_letterboxd_slug_returns_none_on_404(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(status_code=404, url="https://letterboxd.com/tmdb/999999999/")

    slug = resolve_letterboxd_slug(999999999)

    assert slug is None


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_fetch_movie_rating_parses_ld_json(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(status_code=200, text=LD_JSON_HTML)

    rating = fetch_movie_rating("inception")

    assert rating == 4.23


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_fetch_movie_rating_returns_none_on_404(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(status_code=404)

    rating = fetch_movie_rating("nonexistent-film")

    assert rating is None


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_fetch_watchlist_slugs_scrapes_single_page(mock_get, mock_sleep):
    html = '<div data-target-link="/film/the-godfather/"></div><div data-target-link="/film/parasite-2019/"></div>'
    mock_get.return_value = _mock_response(status_code=200, text=html)

    slugs = fetch_watchlist_slugs("someuser")

    assert slugs == {"the-godfather", "parasite-2019"}
    mock_get.assert_called_once_with("https://letterboxd.com/someuser/watchlist/", timeout=10)


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_fetch_watchlist_slugs_follows_pagination(mock_get, mock_sleep):
    page1_html = (
        '<div data-target-link="/film/movie-a/"></div>'
        '<a href="/someuser/watchlist/page/2/">2</a>'
    )
    page2_html = '<div data-target-link="/film/movie-b/"></div>'
    mock_get.side_effect = [
        _mock_response(status_code=200, text=page1_html),
        _mock_response(status_code=200, text=page2_html),
    ]

    slugs = fetch_watchlist_slugs("someuser")

    assert slugs == {"movie-a", "movie-b"}
    assert mock_get.call_count == 2
    mock_get.assert_any_call("https://letterboxd.com/someuser/watchlist/page/2/", timeout=10)


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_fetch_best_of_list_slugs_scrapes_given_url(mock_get, mock_sleep):
    html = '<div data-target-link="/film/the-godfather/"></div>'
    mock_get.return_value = _mock_response(status_code=200, text=html)

    slugs = fetch_best_of_list_slugs("https://letterboxd.com/ctsearles/list/official-top-250-narrative-feature-films/")

    assert slugs == {"the-godfather"}


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_requests_are_paced_with_fixed_delay(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(status_code=200, text="")

    fetch_movie_rating("some-film")

    mock_sleep.assert_called()


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_retries_on_server_error_then_succeeds(mock_get, mock_sleep):
    failing_response = _mock_response(status_code=503)
    ok_response = _mock_response(status_code=200, text=LD_JSON_HTML)
    mock_get.side_effect = [failing_response, ok_response]

    rating = fetch_movie_rating("inception")

    assert rating == 4.23
    assert mock_get.call_count == 2


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_raises_after_exhausting_retries_on_persistent_server_error(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(status_code=500)

    with pytest.raises(HTTPError):
        fetch_movie_rating("some-film")


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_connection_error_is_retried(mock_get, mock_sleep):
    mock_get.side_effect = [CurlConnectionError("boom"), _mock_response(status_code=200, text=LD_JSON_HTML)]

    rating = fetch_movie_rating("inception")

    assert rating == 4.23


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_rate_limit_429_is_retried_not_treated_as_no_match(mock_get, mock_sleep):
    mock_get.side_effect = [_mock_response(status_code=429), _mock_response(status_code=200, url="https://letterboxd.com/film/inception/")]

    slug = resolve_letterboxd_slug(27205)

    assert slug == "inception"
    assert mock_get.call_count == 2


@patch("cinema_recs.letterboxd_client.time.sleep")
@patch("cinema_recs.letterboxd_client._session.get")
def test_persistent_rate_limit_raises_rather_than_returning_none(mock_get, mock_sleep):
    mock_get.return_value = _mock_response(status_code=429)

    with pytest.raises(HTTPError):
        resolve_letterboxd_slug(27205)
