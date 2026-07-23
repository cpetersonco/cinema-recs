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
    ticket_url: Optional[str]
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


@dataclass
class MovieMetadata:
    id: Optional[int]
    movie_title: str
    match_status: str  # "matched" or "unmatched"
    tmdb_id: Optional[int]
    tmdb_title: Optional[str]
    genres: Optional[str]
    overview: Optional[str]
    release_year: Optional[int]
    average_rating: Optional[float]
    runtime_minutes: Optional[int]
    poster_path: Optional[str]
    last_enriched_at: datetime


@dataclass
class EnrichmentAttempt:
    id: Optional[int]
    movie_title: str
    attempted_at: datetime
    outcome: str  # "matched", "unmatched", or "failed"
    error_message: Optional[str]


@dataclass
class LetterboxdMovieData:
    id: Optional[int]
    movie_title: str
    tmdb_id: int
    letterboxd_slug: Optional[str]
    average_rating: Optional[float]
    fetched_at: datetime


@dataclass
class MovieRecommendation:
    id: Optional[int]
    movie_title: str
    is_recommended: bool
    reasons: Optional[str]
    evaluated_at: datetime


@dataclass
class NotificationRecord:
    id: Optional[int]
    movie_title: str
    active: bool
    notified_at: Optional[datetime]
    last_delivery_outcome: Optional[str]  # "sent" or "failed"
