from unittest.mock import patch

import pytest

from cinema_recs import storage
from cinema_recs.config import Config
from cinema_recs.letterboxd_client import BUILT_IN_BEST_OF_LISTS
from cinema_recs.recommend import _refresh_reference_lists, run_recommendation_evaluation


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    storage.init_schema(path)
    return path


def _config(tmp_path, username=None, threshold=None):
    return Config(
        source_url="https://example.com",
        refresh_interval_hours=3,
        data_dir=str(tmp_path),
        port=8080,
        tmdb_api_key="test-tmdb-key",
        letterboxd_username=username,
        letterboxd_rating_threshold=threshold,
        discord_webhook_url=None,
        notifications_enabled=True,
    )


def _seed_matched_movie(db_path, title, tmdb_id=42):
    storage.upsert_movie_metadata(db_path, title, match_status="matched", tmdb_id=tmdb_id)


def _lists_side_effect(matches: dict):
    """Build a fetch_best_of_list_slugs side_effect returning per-list slug
    sets keyed by list_key (looked up by URL, since _refresh_reference_lists
    calls the mock once per BUILT_IN_BEST_OF_LISTS entry with that entry's
    URL). Lists not in `matches` return an empty set."""

    def _fake(url):
        for list_key, slugs in matches.items():
            if url == BUILT_IN_BEST_OF_LISTS[list_key].url:
                return slugs
        return set()

    return _fake


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
def test_zero_config_marks_nothing_recommended_without_network_calls(mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "Some Movie")
    config = _config(tmp_path)

    evaluated = run_recommendation_evaluation(db_path, config)

    assert evaluated == 1
    rec = storage.get_movie_recommendation(db_path, "Some Movie")
    assert rec.is_recommended is False
    assert rec.reasons is None
    mock_watchlist.assert_not_called()
    mock_lists.assert_not_called()


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
def test_movie_on_watchlist_is_recommended(mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "The Great Adventure")
    mock_resolve.return_value = "the-great-adventure"
    mock_watchlist.return_value = {"the-great-adventure"}
    mock_lists.return_value = set()
    config = _config(tmp_path, username="operator")

    with patch("cinema_recs.recommend.fetch_movie_rating", return_value=None):
        run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "The Great Adventure")
    assert rec.is_recommended is True
    assert rec.reasons == "watchlist"


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
@patch("cinema_recs.recommend.fetch_movie_rating")
def test_movie_above_rating_threshold_is_recommended(mock_rating, mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "Highly Rated Movie")
    mock_resolve.return_value = "highly-rated-movie"
    mock_rating.return_value = 4.5
    mock_watchlist.return_value = set()
    mock_lists.return_value = set()
    config = _config(tmp_path, threshold=4.0)

    run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Highly Rated Movie")
    assert rec.is_recommended is True
    assert rec.reasons == "rating"


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
@patch("cinema_recs.recommend.fetch_movie_rating")
def test_movie_below_rating_threshold_is_not_recommended(mock_rating, mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "Mediocre Movie")
    mock_resolve.return_value = "mediocre-movie"
    mock_rating.return_value = 3.0
    mock_watchlist.return_value = set()
    mock_lists.return_value = set()
    config = _config(tmp_path, threshold=4.0)

    run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Mediocre Movie")
    assert rec.is_recommended is False
    assert rec.reasons is None


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
def test_movie_on_best_of_list_is_recommended(mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "Classic Film")
    mock_resolve.return_value = "classic-film"
    mock_watchlist.return_value = set()
    mock_lists.return_value = {"classic-film"}
    config = _config(tmp_path, username="operator")

    with patch("cinema_recs.recommend.fetch_movie_rating", return_value=None):
        run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Classic Film")
    assert rec.is_recommended is True
    assert "Official Top 250 Narrative Feature Films" in rec.reasons


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
def test_movie_on_onboarded_list_only_is_recommended_with_its_display_name(
    mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path
):
    """Feature 013 US1 acceptance scenario 1: a movie on a newly onboarded
    list (and no other criterion) is recommended, with that list's name in
    reasons."""
    _seed_matched_movie(db_path, "Horror Classic")
    mock_resolve.return_value = "horror-classic"
    mock_watchlist.return_value = set()
    mock_lists.side_effect = _lists_side_effect({"top_250_horror": {"horror-classic"}})
    config = _config(tmp_path, username="operator")

    with patch("cinema_recs.recommend.fetch_movie_rating", return_value=None):
        run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Horror Classic")
    assert rec.is_recommended is True
    assert rec.reasons == "Top 250 Horror Films"


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
def test_movie_on_multiple_onboarded_lists_has_every_list_in_reasons(
    mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path
):
    """Feature 013 US1 acceptance scenario 2: a movie on more than one
    onboarded list has every matching list named in reasons."""
    _seed_matched_movie(db_path, "Beloved Animated Classic")
    mock_resolve.return_value = "beloved-animated-classic"
    mock_watchlist.return_value = set()
    mock_lists.side_effect = _lists_side_effect(
        {
            "official_top_250": {"beloved-animated-classic"},
            "top_250_animated": {"beloved-animated-classic"},
        }
    )
    config = _config(tmp_path, username="operator")

    with patch("cinema_recs.recommend.fetch_movie_rating", return_value=None):
        run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Beloved Animated Classic")
    assert rec.is_recommended is True
    assert "Official Top 250 Narrative Feature Films" in rec.reasons
    assert "Top 250 Animated Films" in rec.reasons


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
def test_movie_on_no_onboarded_list_is_not_recommended(mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    """Feature 013 US1 acceptance scenario 3."""
    _seed_matched_movie(db_path, "Unranked Movie")
    mock_resolve.return_value = "unranked-movie"
    mock_watchlist.return_value = set()
    mock_lists.return_value = set()
    config = _config(tmp_path, username="operator")

    with patch("cinema_recs.recommend.fetch_movie_rating", return_value=None):
        run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Unranked Movie")
    assert rec.is_recommended is False
    assert rec.reasons is None


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
def test_movie_with_no_letterboxd_match_is_never_recommended(mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "Obscure Movie")
    mock_resolve.return_value = None
    mock_watchlist.return_value = {"some-other-film"}
    mock_lists.return_value = set()
    config = _config(tmp_path, username="operator")

    run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Obscure Movie")
    assert rec.is_recommended is False
    assert rec.reasons is None


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
def test_does_not_relookup_already_cached_letterboxd_data(mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "Cached Movie")
    storage.upsert_letterboxd_movie_data(db_path, "Cached Movie", tmdb_id=42, letterboxd_slug="cached-movie", average_rating=3.5)
    mock_watchlist.return_value = set()
    mock_lists.return_value = set()
    config = _config(tmp_path, username="operator")

    run_recommendation_evaluation(db_path, config)

    mock_resolve.assert_not_called()


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
def test_failed_watchlist_refresh_keeps_stale_cache(mock_watchlist, mock_lists, db_path, tmp_path):
    _seed_matched_movie(db_path, "Watchlisted Movie")
    storage.upsert_letterboxd_movie_data(db_path, "Watchlisted Movie", tmdb_id=42, letterboxd_slug="watchlisted-movie", average_rating=3.5)
    storage.replace_reference_list_slugs(db_path, "watchlist", {"watchlisted-movie"})
    mock_watchlist.side_effect = Exception("network error")
    mock_lists.return_value = set()
    config = _config(tmp_path, username="operator")

    run_recommendation_evaluation(db_path, config)

    rec = storage.get_movie_recommendation(db_path, "Watchlisted Movie")
    assert rec.is_recommended is True
    assert rec.reasons == "watchlist"


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
def test_one_onboarded_list_failure_does_not_affect_other_lists(mock_lists, db_path, tmp_path):
    """Feature 013 US2: a fetch failure against one onboarded list's page
    keeps that list's previously cached membership untouched and does not
    block the other onboarded lists from refreshing in the same cycle."""
    storage.replace_reference_list_slugs(db_path, "best_of:top_250_horror", {"stale-horror-film"})
    storage.replace_reference_list_slugs(db_path, "best_of:top_250_animated", {"stale-animated-film"})

    def _fake(url):
        if url == BUILT_IN_BEST_OF_LISTS["top_250_horror"].url:
            raise Exception("network error")
        if url == BUILT_IN_BEST_OF_LISTS["top_250_animated"].url:
            return {"fresh-animated-film"}
        return set()

    mock_lists.side_effect = _fake
    config = _config(tmp_path)

    _refresh_reference_lists(db_path, config)

    assert storage.get_reference_list_slugs(db_path, "best_of:top_250_horror") == {"stale-horror-film"}
    assert storage.get_reference_list_slugs(db_path, "best_of:top_250_animated") == {"fresh-animated-film"}


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
def test_one_onboarded_list_failure_logs_only_for_that_list(mock_lists, db_path, tmp_path, caplog):
    def _fake(url):
        if url == BUILT_IN_BEST_OF_LISTS["top_250_horror"].url:
            raise Exception("network error")
        return set()

    mock_lists.side_effect = _fake
    config = _config(tmp_path)

    with caplog.at_level("ERROR", logger="cinema_recs.recommend"):
        _refresh_reference_lists(db_path, config)

    failure_messages = [r.getMessage() for r in caplog.records]
    assert any("top_250_horror" in msg for msg in failure_messages)
    assert not any("top_250_animated" in msg for msg in failure_messages)


@patch("cinema_recs.recommend.fetch_best_of_list_slugs")
@patch("cinema_recs.recommend.fetch_watchlist_slugs")
@patch("cinema_recs.recommend.resolve_letterboxd_slug")
@patch("cinema_recs.recommend.fetch_movie_rating")
def test_threshold_change_unmarks_and_marks_showtimes_on_next_evaluation(mock_rating, mock_resolve, mock_watchlist, mock_lists, db_path, tmp_path):
    mock_watchlist.return_value = set()
    mock_lists.return_value = set()

    _seed_matched_movie(db_path, "Borderline Movie A")
    _seed_matched_movie(db_path, "Borderline Movie B")
    mock_resolve.side_effect = ["movie-a", "movie-b"]
    mock_rating.side_effect = [4.2, 3.8]

    config_first = _config(tmp_path, threshold=4.0)
    run_recommendation_evaluation(db_path, config_first)

    rec_a_first = storage.get_movie_recommendation(db_path, "Borderline Movie A")
    rec_b_first = storage.get_movie_recommendation(db_path, "Borderline Movie B")
    assert rec_a_first.is_recommended is True
    assert rec_b_first.is_recommended is False

    config_second = _config(tmp_path, threshold=4.3)
    run_recommendation_evaluation(db_path, config_second)

    rec_a_second = storage.get_movie_recommendation(db_path, "Borderline Movie A")
    assert rec_a_second.is_recommended is False
