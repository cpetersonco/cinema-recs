import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
REQUEST_PACING_SECONDS = 0.25
MAX_RETRIES = 2


@dataclass
class TmdbSearchResult:
    tmdb_id: int
    title: str
    popularity: float
    vote_count: int
    release_year: Optional[int]


@dataclass
class TmdbMovieDetails:
    tmdb_id: int
    title: str
    genres: list[str]
    overview: str
    release_year: Optional[int]
    average_rating: float
    runtime_minutes: Optional[int]
    poster_path: Optional[str]


@dataclass
class MatchResult:
    status: str  # "matched", "unmatched", or "ambiguous"
    tmdb_id: Optional[int] = None


def _get_with_retry(url: str, params: dict) -> dict:
    """Fixed-delay pacing before each call (research.md), retrying transient
    failures up to MAX_RETRIES times before giving up."""
    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):
        time.sleep(REQUEST_PACING_SECONDS)
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:  # noqa: PERF203 - retry loop is intentional
            last_exc = exc
            if attempt < MAX_RETRIES:
                logger.warning("TMDB request failed (attempt %d), retrying: %s", attempt + 1, exc)
    raise last_exc


def search_movie(api_key: str, title: str) -> list[TmdbSearchResult]:
    """Search TMDB for a movie title, paced with a fixed delay per research.md."""
    data = _get_with_retry(
        f"{TMDB_BASE_URL}/search/movie",
        params={"api_key": api_key, "query": title},
    )
    results = []
    for item in data.get("results", []):
        release_date = item.get("release_date") or ""
        release_year = int(release_date[:4]) if release_date[:4].isdigit() else None
        results.append(
            TmdbSearchResult(
                tmdb_id=item["id"],
                title=item.get("title", ""),
                popularity=item.get("popularity", 0.0),
                vote_count=item.get("vote_count", 0),
                release_year=release_year,
            )
        )
    return results


def get_movie_details(api_key: str, tmdb_id: int) -> TmdbMovieDetails:
    data = _get_with_retry(
        f"{TMDB_BASE_URL}/movie/{tmdb_id}",
        params={"api_key": api_key},
    )
    release_date = data.get("release_date") or ""
    release_year = int(release_date[:4]) if release_date[:4].isdigit() else None
    return TmdbMovieDetails(
        tmdb_id=data["id"],
        title=data.get("title", ""),
        genres=[g["name"] for g in data.get("genres", [])],
        overview=data.get("overview", ""),
        release_year=release_year,
        average_rating=data.get("vote_average", 0.0),
        runtime_minutes=data.get("runtime"),
        poster_path=data.get("poster_path"),
    )


# Cinepolis prefixes some listings with a discounted-screening promo price
# (e.g. "$5 The Mask" for a $5 re-release showing) that TMDB has no concept
# of, so it must be stripped before searching/matching or it causes an
# otherwise-clean title to spuriously miss (verified against live Cinepolis
# ingestion, where "$5 The Mask" failed to match "The Mask").
_PROMO_PRICE_PREFIX_RE = re.compile(r"^\$\d+(\.\d+)?\s+")


def strip_promo_price_prefix(title: str) -> str:
    return _PROMO_PRICE_PREFIX_RE.sub("", title)


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", strip_promo_price_prefix(title).lower())


def match_title(title: str, results: list[TmdbSearchResult]) -> MatchResult:
    """Accept the top TMDB search result only when it's a clearly-best match
    (normalized title equality), rejecting ambiguous or absent results rather
    than guessing (spec FR-004, research.md)."""
    if not results:
        return MatchResult(status="unmatched")

    normalized_target = _normalize_title(title)
    exact_matches = [r for r in results if _normalize_title(r.title) == normalized_target]

    if len(exact_matches) == 1:
        return MatchResult(status="matched", tmdb_id=exact_matches[0].tmdb_id)

    if len(exact_matches) > 1:
        # Multiple exact-title matches (e.g. remakes) — pick the clearly-best
        # one only if its popularity/vote_count clearly leads; else ambiguous.
        ranked = sorted(exact_matches, key=lambda r: r.vote_count, reverse=True)
        top, runner_up = ranked[0], ranked[1]
        if top.vote_count > 0 and runner_up.vote_count > 0 and top.vote_count <= runner_up.vote_count * 1.5:
            return MatchResult(status="ambiguous")
        return MatchResult(status="matched", tmdb_id=top.tmdb_id)

    return MatchResult(status="unmatched")
