import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Config:
    source_url: str
    refresh_interval_hours: float
    data_dir: str
    port: int
    tmdb_api_key: str
    letterboxd_username: Optional[str]
    letterboxd_rating_threshold: Optional[float]

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "cinema_recs.db")


def _load_letterboxd_rating_threshold() -> Optional[float]:
    """Invalid/non-numeric values are treated as unset (spec FR-008),
    never as a startup error."""
    raw = os.environ.get("LETTERBOXD_RATING_THRESHOLD")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        logger.warning("Ignoring non-numeric LETTERBOXD_RATING_THRESHOLD=%r", raw)
        return None


def load_config() -> Config:
    source_url = os.environ.get("CINEMA_RECS_SOURCE_URL")
    if not source_url:
        raise RuntimeError("CINEMA_RECS_SOURCE_URL environment variable is required")

    tmdb_api_key = os.environ.get("TMDB_API_KEY")
    if not tmdb_api_key:
        raise RuntimeError("TMDB_API_KEY environment variable is required")

    refresh_interval_hours = float(os.environ.get("CINEMA_RECS_REFRESH_INTERVAL_HOURS", "3"))
    data_dir = os.environ.get("CINEMA_RECS_DATA_DIR", "/data")
    port = int(os.environ.get("CINEMA_RECS_PORT", "8080"))
    letterboxd_username = os.environ.get("LETTERBOXD_USERNAME") or None
    letterboxd_rating_threshold = _load_letterboxd_rating_threshold()

    return Config(
        source_url=source_url,
        refresh_interval_hours=refresh_interval_hours,
        data_dir=data_dir,
        port=port,
        tmdb_api_key=tmdb_api_key,
        letterboxd_username=letterboxd_username,
        letterboxd_rating_threshold=letterboxd_rating_threshold,
    )
