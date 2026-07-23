import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


TEXAS_THEATRE_NAME = "Texas Theatre"
TEXAS_THEATRE_LOCATION = "Oak Cliff, Dallas, TX"
TEXAS_THEATRE_DEFAULT_URL = "https://thetexastheatre.com/calendar"

ANGELIKA_DALLAS_NAME = "Angelika Film Center Dallas"
ANGELIKA_DALLAS_LOCATION = "Dallas, TX"
ANGELIKA_DALLAS_DEFAULT_URL = "https://angelikafilmcenter.com/dallas"

CINEMARK_WEST_PLANO_NAME = "Cinemark West Plano XD and ScreenX"
CINEMARK_WEST_PLANO_LOCATION = "Plano, TX"
CINEMARK_WEST_PLANO_DEFAULT_URL = (
    "https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx"
)
# Cinemark's internal theater ID for West Plano — the `theaterId` query param
# on every `GetByTheaterId` showtimes request and `TicketSeatMap` ticket link
# (confirmed via live network inspection, spec 012 research.md §1).
CINEMARK_WEST_PLANO_THEATER_ID = "231"


@dataclass(frozen=True)
class Config:
    source_url: str
    refresh_interval_hours: float
    data_dir: str
    port: int
    tmdb_api_key: str
    letterboxd_username: Optional[str]
    letterboxd_rating_threshold: Optional[float]
    discord_webhook_url: Optional[str]
    notifications_enabled: bool

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


def _load_notifications_enabled() -> bool:
    """Enabled by default once a webhook URL is configured — the switch
    exists to pause delivery without discarding the URL, not to require a
    second explicit opt-in (spec FR-006, research.md)."""
    raw = os.environ.get("NOTIFICATIONS_ENABLED")
    if not raw:
        return True
    return raw.strip().lower() not in ("false", "0", "no")


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
    discord_webhook_url = os.environ.get("DISCORD_WEBHOOK_URL") or None
    notifications_enabled = _load_notifications_enabled()

    return Config(
        source_url=source_url,
        refresh_interval_hours=refresh_interval_hours,
        data_dir=data_dir,
        port=port,
        tmdb_api_key=tmdb_api_key,
        letterboxd_username=letterboxd_username,
        letterboxd_rating_threshold=letterboxd_rating_threshold,
        discord_webhook_url=discord_webhook_url,
        notifications_enabled=notifications_enabled,
    )
