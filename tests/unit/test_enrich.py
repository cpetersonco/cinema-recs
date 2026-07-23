from datetime import date, datetime, time
from unittest.mock import patch

import pytest

from cinema_recs import storage
from cinema_recs.enrich import run_enrichment
from cinema_recs.tmdb_client import MatchResult, TmdbMovieDetails, TmdbSearchResult


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


def _seed_showtime(db_path, cinema, movie_title):
    storage.upsert_showtime(
        db_path, cinema.id, movie_title, date(2026, 8, 1), time(18, 0), None,
        datetime(2026, 8, 1, 10, 0, 0),
    )


@patch("cinema_recs.enrich.get_movie_details")
@patch("cinema_recs.enrich.match_title")
@patch("cinema_recs.enrich.search_movie")
def test_run_enrichment_stores_matched_metadata(mock_search, mock_match, mock_details, db_path, cinema):
    _seed_showtime(db_path, cinema, "The Great Adventure")
    mock_search.return_value = [TmdbSearchResult(42, "The Great Adventure", 1.0, 100, 2024)]
    mock_match.return_value = MatchResult(status="matched", tmdb_id=42)
    mock_details.return_value = TmdbMovieDetails(
        tmdb_id=42, title="The Great Adventure", genres=["Action"], overview="...",
        release_year=2024, average_rating=7.5, runtime_minutes=118, poster_path="/p.jpg",
    )

    attempted = run_enrichment(db_path, "fake-key")

    assert attempted == 1
    metadata = storage.get_movie_metadata(db_path, "The Great Adventure")
    assert metadata.match_status == "matched"
    assert metadata.tmdb_id == 42
    assert metadata.genres == "Action"


@patch("cinema_recs.enrich.match_title")
@patch("cinema_recs.enrich.search_movie")
def test_run_enrichment_does_not_relookup_already_enriched_titles(mock_search, mock_match, db_path, cinema):
    _seed_showtime(db_path, cinema, "The Great Adventure")
    storage.upsert_movie_metadata(db_path, "The Great Adventure", match_status="matched", tmdb_id=42)

    attempted = run_enrichment(db_path, "fake-key")

    assert attempted == 0
    mock_search.assert_not_called()
    mock_match.assert_not_called()


@patch("cinema_recs.enrich.match_title")
@patch("cinema_recs.enrich.search_movie")
def test_run_enrichment_records_explicit_unmatched_row(mock_search, mock_match, db_path, cinema):
    _seed_showtime(db_path, cinema, "Obscure Title")
    mock_search.return_value = []
    mock_match.return_value = MatchResult(status="unmatched")

    run_enrichment(db_path, "fake-key")

    metadata = storage.get_movie_metadata(db_path, "Obscure Title")
    assert metadata is not None
    assert metadata.match_status == "unmatched"
    assert metadata.tmdb_id is None


@patch("cinema_recs.enrich.match_title")
@patch("cinema_recs.enrich.search_movie")
def test_run_enrichment_records_ambiguous_as_unmatched(mock_search, mock_match, db_path, cinema):
    _seed_showtime(db_path, cinema, "The Great Adventure")
    mock_search.return_value = [
        TmdbSearchResult(1, "The Great Adventure", 1.0, 100, 2024),
        TmdbSearchResult(2, "The Great Adventure", 1.0, 90, 1999),
    ]
    mock_match.return_value = MatchResult(status="ambiguous")

    run_enrichment(db_path, "fake-key")

    metadata = storage.get_movie_metadata(db_path, "The Great Adventure")
    assert metadata.match_status == "unmatched"
    assert metadata.tmdb_id is None
