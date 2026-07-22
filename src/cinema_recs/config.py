import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    source_url: str
    refresh_interval_hours: float
    data_dir: str
    port: int

    @property
    def db_path(self) -> str:
        return os.path.join(self.data_dir, "cinema_recs.db")


def load_config() -> Config:
    source_url = os.environ.get("CINEMA_RECS_SOURCE_URL")
    if not source_url:
        raise RuntimeError("CINEMA_RECS_SOURCE_URL environment variable is required")

    refresh_interval_hours = float(os.environ.get("CINEMA_RECS_REFRESH_INTERVAL_HOURS", "3"))
    data_dir = os.environ.get("CINEMA_RECS_DATA_DIR", "/data")
    port = int(os.environ.get("CINEMA_RECS_PORT", "8080"))

    return Config(
        source_url=source_url,
        refresh_interval_hours=refresh_interval_hours,
        data_dir=data_dir,
        port=port,
    )
