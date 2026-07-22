from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional


@dataclass
class Cinema:
    id: Optional[int]
    name: str
    location: str
    source_url: str
    created_at: datetime


@dataclass
class Showtime:
    id: Optional[int]
    cinema_id: int
    movie_title: str
    show_date: date
    start_time: time
    format: Optional[str]
    first_seen_at: datetime
    last_seen_at: datetime
    status: str  # "active" or "stale"


@dataclass
class IngestionRun:
    id: Optional[int]
    cinema_id: int
    started_at: datetime
    finished_at: Optional[datetime]
    outcome: str  # "success", "failure", or "partial"
    showtimes_captured: int
    error_message: Optional[str]
