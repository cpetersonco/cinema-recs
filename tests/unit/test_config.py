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
