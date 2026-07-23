import pytest

from cinema_recs.config import load_config


def test_load_config_reads_env_vars(monkeypatch):
    monkeypatch.setenv("CINEMA_RECS_SOURCE_URL", "https://example.com/mckinney")
    monkeypatch.setenv("CINEMA_RECS_REFRESH_INTERVAL_HOURS", "4")
    monkeypatch.setenv("CINEMA_RECS_DATA_DIR", "/tmp/data")
    monkeypatch.setenv("CINEMA_RECS_PORT", "9090")

    config = load_config()

    assert config.source_url == "https://example.com/mckinney"
    assert config.refresh_interval_hours == 4
    assert config.data_dir == "/tmp/data"
    assert config.port == 9090
    assert config.db_path == "/tmp/data/cinema_recs.db"


def test_load_config_uses_defaults_when_optional_vars_missing(monkeypatch):
    monkeypatch.setenv("CINEMA_RECS_SOURCE_URL", "https://example.com/mckinney")
    monkeypatch.delenv("CINEMA_RECS_REFRESH_INTERVAL_HOURS", raising=False)
    monkeypatch.delenv("CINEMA_RECS_DATA_DIR", raising=False)
    monkeypatch.delenv("CINEMA_RECS_PORT", raising=False)

    config = load_config()

    assert config.refresh_interval_hours == 3
    assert config.data_dir == "/data"
    assert config.port == 8080


def test_load_config_raises_without_source_url(monkeypatch):
    monkeypatch.delenv("CINEMA_RECS_SOURCE_URL", raising=False)

    with pytest.raises(RuntimeError):
        load_config()


def test_load_config_letterboxd_settings_default_to_unset(monkeypatch):
    monkeypatch.setenv("CINEMA_RECS_SOURCE_URL", "https://example.com/mckinney")
    monkeypatch.setenv("TMDB_API_KEY", "tmdb-key")
    monkeypatch.delenv("LETTERBOXD_USERNAME", raising=False)
    monkeypatch.delenv("LETTERBOXD_RATING_THRESHOLD", raising=False)

    config = load_config()

    assert config.letterboxd_username is None
    assert config.letterboxd_rating_threshold is None


def test_load_config_reads_letterboxd_settings(monkeypatch):
    monkeypatch.setenv("CINEMA_RECS_SOURCE_URL", "https://example.com/mckinney")
    monkeypatch.setenv("TMDB_API_KEY", "tmdb-key")
    monkeypatch.setenv("LETTERBOXD_USERNAME", "daveyj")
    monkeypatch.setenv("LETTERBOXD_RATING_THRESHOLD", "4.0")

    config = load_config()

    assert config.letterboxd_username == "daveyj"
    assert config.letterboxd_rating_threshold == 4.0


def test_load_config_treats_invalid_rating_threshold_as_unset(monkeypatch):
    monkeypatch.setenv("CINEMA_RECS_SOURCE_URL", "https://example.com/mckinney")
    monkeypatch.setenv("TMDB_API_KEY", "tmdb-key")
    monkeypatch.setenv("LETTERBOXD_RATING_THRESHOLD", "not-a-number")

    config = load_config()

    assert config.letterboxd_rating_threshold is None
