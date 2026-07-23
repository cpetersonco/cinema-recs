from unittest.mock import MagicMock

import pytest

import main
from cinema_recs.scraper import ScrapeResult


@pytest.fixture
def base_env(monkeypatch, tmp_path):
    """Required config plus every optional feature deliberately left
    unconfigured, so run_enrichment/run_recommendation_evaluation/
    run_notifications each take their own documented "nothing configured"
    fast path (enrich.py: no showtimes -> no titles to look up;
    recommend.py FR-005: no Letterboxd criteria -> zero Letterboxd
    requests; notify.py: no webhook -> return 0 immediately) — meaning a
    full one-shot pass needs no TMDB/Letterboxd/Discord mocking at all,
    only the three scrapers below."""
    monkeypatch.setenv("CINEMA_RECS_SOURCE_URL", "https://example.com/mckinney")
    monkeypatch.setenv("TMDB_API_KEY", "test-tmdb-key")
    monkeypatch.setenv("CINEMA_RECS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CINEMA_RECS_PORT", "8080")
    monkeypatch.delenv("LETTERBOXD_USERNAME", raising=False)
    monkeypatch.delenv("LETTERBOXD_RATING_THRESHOLD", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)


@pytest.fixture
def mock_scrapers(monkeypatch):
    empty = ScrapeResult(showtimes=[], reported_count=0, complete=True)
    monkeypatch.setattr("cinema_recs.ingest.scrape_showtimes", lambda url: empty)
    monkeypatch.setattr("cinema_recs.ingest.scrape_texas_theatre_showtimes", lambda url: empty)
    monkeypatch.setattr("cinema_recs.ingest.scrape_angelika_dallas_showtimes", lambda url: empty)
    monkeypatch.setattr("cinema_recs.ingest.scrape_amc_stonebriar_showtimes", lambda url: empty)
    monkeypatch.setattr(
        "cinema_recs.ingest.scrape_cinemark_west_plano_showtimes", lambda url: empty
    )


def test_bootstrap_configures_all_cinemas_with_correct_source_type(base_env):
    config, cinemas = main.bootstrap()

    by_name = {c.name: c for c in cinemas}
    assert set(by_name) == {
        "Cinepolis McKinney",
        "Texas Theatre",
        "Angelika Film Center Dallas",
        "AMC Stonebriar 24",
        "Cinemark West Plano XD and ScreenX",
    }
    assert by_name["Cinepolis McKinney"].source_type == "cinepolis"
    assert by_name["Texas Theatre"].source_type == "texas_theatre"
    assert by_name["Angelika Film Center Dallas"].source_type == "angelika_dallas"
    assert by_name["AMC Stonebriar 24"].source_type == "amc_stonebriar"
    assert by_name["Cinemark West Plano XD and ScreenX"].source_type == "cinemark_west_plano"

    # init_schema was applied - the cinema table is queryable with the
    # columns bootstrap() actually populated.
    from cinema_recs import storage
    assert storage.get_cinema_by_name(config.db_path, "Cinepolis McKinney") is not None


def test_main_ingest_once_mode_returns_without_starting_scheduler_or_server(
    base_env, mock_scrapers, monkeypatch
):
    monkeypatch.setattr("sys.argv", ["main.py", "ingest-once"])
    mock_start_scheduler = MagicMock()
    mock_create_app = MagicMock()
    monkeypatch.setattr("main.start_scheduler", mock_start_scheduler)
    monkeypatch.setattr("main.create_app", mock_create_app)

    main.main()

    mock_start_scheduler.assert_not_called()
    mock_create_app.assert_not_called()


def test_main_default_mode_starts_scheduler_and_runs_server(base_env, mock_scrapers, monkeypatch):
    monkeypatch.setattr("sys.argv", ["main.py"])
    mock_start_scheduler = MagicMock()
    mock_app = MagicMock()
    mock_create_app = MagicMock(return_value=mock_app)
    monkeypatch.setattr("main.start_scheduler", mock_start_scheduler)
    monkeypatch.setattr("main.create_app", mock_create_app)

    main.main()

    mock_start_scheduler.assert_called_once()
    args, _ = mock_start_scheduler.call_args
    config, cinemas = args
    assert len(cinemas) == 5

    mock_create_app.assert_called_once_with(config, cinemas)
    mock_app.run.assert_called_once_with(host="0.0.0.0", port=config.port)
