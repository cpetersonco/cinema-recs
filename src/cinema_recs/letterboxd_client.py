import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from curl_cffi import requests
from curl_cffi.requests.exceptions import HTTPError, RequestException

logger = logging.getLogger(__name__)

BASE_URL = "https://letterboxd.com"
REQUEST_PACING_SECONDS = 0.25
MAX_RETRIES = 2


@dataclass(frozen=True)
class BestOfList:
    """A built-in Letterboxd list checked as a recommendation criterion.

    `display_name` is shown verbatim to the operator (web view, Discord
    notifications) wherever a matched recommendation reason is surfaced.
    """

    display_name: str
    url: str


BUILT_IN_BEST_OF_LISTS: dict[str, BestOfList] = {
    # Community-maintained clone of Letterboxd's own official ratings-based
    # ranking under this exact name (research.md: Letterboxd's own "official"
    # curator account hosts a different set of editorial lists, not this one).
    "official_top_250": BestOfList(
        display_name="Official Top 250 Narrative Feature Films",
        url=f"{BASE_URL}/ctsearles/list/official-top-250-narrative-feature-films/",
    ),
    # The remaining lists are hosted directly under Letterboxd's own
    # letterboxd.com/official/ curator account (feature 013 research.md:
    # live-verified 200s with the same data-target-link/pagination markup
    # this module already parses).
    "top_500": BestOfList(
        display_name="Letterboxd's Top 500 Films",
        url=f"{BASE_URL}/official/list/letterboxds-top-500-films/",
    ),
    "most_fans": BestOfList(
        display_name="Top 250 Films with the Most Fans",
        url=f"{BASE_URL}/official/list/top-250-films-with-the-most-fans/",
    ),
    "top_250_animated": BestOfList(
        display_name="Top 250 Animated Films",
        url=f"{BASE_URL}/official/list/top-250-animated-films/",
    ),
    "top_250_horror": BestOfList(
        display_name="Top 250 Horror Films",
        url=f"{BASE_URL}/official/list/top-250-horror-films/",
    ),
    "top_250_documentary": BestOfList(
        display_name="Top 250 Documentary Films",
        url=f"{BASE_URL}/official/list/top-250-documentary-films/",
    ),
    "top_250_women_directors": BestOfList(
        display_name="Top 250 Films by Women Directors",
        url=f"{BASE_URL}/official/list/top-250-films-by-women-directors/",
    ),
    "top_250_black_directors": BestOfList(
        display_name="Top 250 Films by Black Directors",
        url=f"{BASE_URL}/official/list/top-250-films-by-black-directors/",
    ),
    "top_100_underseen": BestOfList(
        display_name="Top 100 Underseen Films",
        url=f"{BASE_URL}/official/list/top-100-underseen-films/",
    ),
}

_FILM_SLUG_RE = re.compile(r"/film/([^/]+)/")
_TARGET_LINK_SLUG_RE = re.compile(r'data-target-link="/film/([^/]+)/"')
_PAGE_NUMBER_RE = re.compile(r"/page/(\d+)/")
_LD_JSON_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

# A plain requests.get() against letterboxd.com is liable to trip
# Cloudflare's anonymous-scraping rate limit under any real request volume
# (observed live during development). curl_cffi's TLS/JA3 fingerprint
# impersonation plus a realistic browser header set — the same approach
# github.com/mBaratta96/letterboxd_stats uses — makes traffic indistinguishable
# from a real Firefox session at the network level, which is what actually
# avoids the block; polite pacing alone was not sufficient.
_session = requests.Session(impersonate="firefox133")
_session.headers.update(
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Sec-GPC": "1",
    }
)


def _get_with_retry(url: str) -> requests.Response:
    """Fixed-delay pacing before each call, retrying transient (connection
    error / 5xx / 429 rate-limit) failures up to MAX_RETRIES times before
    giving up. Other 4xx responses (e.g. 404 for "no such page") are
    returned as-is for the caller to interpret, not retried."""
    last_exc: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):
        time.sleep(REQUEST_PACING_SECONDS)
        try:
            response = _session.get(url, timeout=10)
            if response.status_code >= 500 or response.status_code == 429:
                raise HTTPError(f"{response.status_code} error for {url}")
            return response
        except RequestException as exc:  # noqa: PERF203 - retry loop is intentional
            last_exc = exc
            if attempt < MAX_RETRIES:
                logger.warning("Letterboxd request failed (attempt %d), retrying: %s", attempt + 1, exc)
    raise last_exc


def _raise_for_unexpected_status(response: requests.Response) -> None:
    """404 is a meaningful "no such page" result callers interpret
    themselves; anything else non-2xx here means _get_with_retry gave up
    retrying (e.g. a persistent 429) and must not be silently treated as
    "no match" — the caller needs to see this as a failure."""
    if response.status_code != 404 and not response.ok:
        raise HTTPError(f"{response.status_code} error for {response.url}")


def resolve_letterboxd_slug(tmdb_id: int) -> Optional[str]:
    """Resolve a TMDB id to its Letterboxd film slug via the
    letterboxd.com/tmdb/{id}/ redirect (spec FR-012). Returns None if no
    Letterboxd page exists for this TMDB id."""
    response = _get_with_retry(f"{BASE_URL}/tmdb/{tmdb_id}/")
    if response.status_code == 404:
        return None
    _raise_for_unexpected_status(response)
    match = _FILM_SLUG_RE.search(response.url)
    return match.group(1) if match else None


def fetch_movie_rating(slug: str) -> Optional[float]:
    """Fetch a film's Letterboxd average rating (0.5-5 scale) from its
    JSON-LD aggregateRating block."""
    response = _get_with_retry(f"{BASE_URL}/film/{slug}/")
    if response.status_code == 404:
        return None
    _raise_for_unexpected_status(response)

    match = _LD_JSON_RE.search(response.text)
    if not match:
        return None

    raw_json = match.group(1).strip()
    # Letterboxd wraps its ld+json payload in a CDATA comment:
    # "/* <![CDATA[ */ {...} /* ]]> */" — strip that wrapper before parsing.
    raw_json = re.sub(r"^/\*.*?\*/", "", raw_json).strip()
    raw_json = re.sub(r"/\*.*?\*/$", "", raw_json).strip()

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning("Could not parse Letterboxd JSON-LD for film %r", slug)
        return None

    rating = data.get("aggregateRating", {}).get("ratingValue")
    return float(rating) if rating is not None else None


def _fetch_paginated_slugs(base_url: str) -> set[str]:
    """Scrape film slugs from a paginated Letterboxd poster grid (a
    watchlist or list page), following `.../page/{n}/` until the last page
    advertised by the first page's own pagination links."""
    slugs: set[str] = set()
    page = 1
    max_page = 1

    while page <= max_page:
        url = base_url if page == 1 else f"{base_url}page/{page}/"
        response = _get_with_retry(url)
        if response.status_code == 404:
            break
        _raise_for_unexpected_status(response)

        slugs.update(_TARGET_LINK_SLUG_RE.findall(response.text))

        if page == 1:
            page_numbers = [int(n) for n in _PAGE_NUMBER_RE.findall(response.text)]
            if page_numbers:
                max_page = max(page_numbers)

        page += 1

    return slugs


def fetch_watchlist_slugs(username: str) -> set[str]:
    """Scrape every film slug on the operator's public Letterboxd watchlist
    (spec FR-009)."""
    return _fetch_paginated_slugs(f"{BASE_URL}/{username}/watchlist/")


def fetch_best_of_list_slugs(list_url: str) -> set[str]:
    """Scrape every film slug on a built-in best-of list page (spec
    FR-010)."""
    return _fetch_paginated_slugs(list_url)
