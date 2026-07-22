import json
import logging
import time as time_module
from datetime import date, datetime, time
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

MAX_FETCH_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5

REALISTIC_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Cinepolis' site is a Vue/Quasar single-page app with no server-rendered
# showtime markup; it fetches showings from a GraphQL API at runtime,
# authorized per-request via these two custom headers rather than a
# session cookie. Values below are specific to the Cinepolis McKinney
# location (the sole "alpha" cinema for this phase, per spec FR-001) and
# were obtained by inspecting the site's own network traffic while
# navigating to https://www.cinepolisusa.com/mckinney/showtimes.
MCKINNEY_SITE_ID = "168"
CINEPOLIS_CIRCUIT_ID = "89"
CENTRAL_TIME = ZoneInfo("America/Chicago")

# Markers that indicate Cloudflare (or similar) served a bot-challenge/block
# page instead of real content, so callers can tell "blocked" apart from
# a genuine API/parse failure.
BLOCK_PAGE_MARKERS = (
    "Sorry, you have been blocked",
    "Attention Required! | Cloudflare",
    "cf-error-details",
)

SHOWINGS_FOR_DATE_QUERY = """
query ($date: String, $siteIds: [ID]) {
  showingsForDate(date: $date, siteIds: $siteIds) {
    data {
      id
      time
      screenId
      movie {
        id
        name
      }
    }
    count
  }
}
"""


class ScrapedShowtime(NamedTuple):
    movie_title: str
    show_date: date
    start_time: time
    format: str | None


class BlockedError(RuntimeError):
    """Raised when the source appears to have served a bot-protection
    challenge/block page instead of real content."""


def looks_blocked(html: str) -> bool:
    return any(marker in html for marker in BLOCK_PAGE_MARKERS)


def fetch_showings_json(
    source_url: str, show_date: date, timeout_ms: int = 30_000
) -> dict[str, Any]:
    """Fetch raw showtime data for the given date from Cinepolis' GraphQL
    API.

    A real headless browser (with stealth evasions + a realistic
    user-agent) is required just to load `source_url` once, because
    Cinepolis' site is behind Cloudflare bot protection that blocks plain
    HTTP requests and default headless Chromium alike. The actual
    showtime data does not come from that page's HTML though — it's a
    client-side-rendered SPA with no showtime markup in the DOM. Instead,
    once the page is loaded (which establishes the browser as a trusted
    session with Cloudflare), a `fetch()` call is made *from within that
    page's own JS context* (via `page.evaluate`) directly against the
    site's GraphQL endpoint. This matters: the same call made via a
    separate HTTP client (`requests`, or even Playwright's own
    `page.request` API context) gets blocked by Cloudflare, because it
    doesn't carry the real browser's TLS/JS fingerprint - only a `fetch()`
    executed by the already-loaded page does.

    Transient failures (timeouts, navigation errors, detected block
    pages) are retried a few times with a short backoff before giving up.
    """
    last_error: Exception | None = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with Stealth().use_sync(sync_playwright()) as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(
                        user_agent=REALISTIC_USER_AGENT,
                        viewport={"width": 1920, "height": 1080},
                    )
                    page.goto(source_url, timeout=timeout_ms, wait_until="networkidle")

                    if looks_blocked(page.content()):
                        raise BlockedError(
                            f"Source appears to have served a block/challenge page: {source_url}"
                        )

                    result = page.evaluate(
                        """
                        async ({ query, variables, siteId, circuitId }) => {
                            const resp = await fetch('/graphql', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'site-id': siteId,
                                    'circuit-id': circuitId,
                                    'client-type': 'consumer',
                                    'is-electron-mode': 'false',
                                },
                                body: JSON.stringify({ query, variables }),
                            });
                            const text = await resp.text();
                            return { status: resp.status, text };
                        }
                        """,
                        {
                            "query": SHOWINGS_FOR_DATE_QUERY,
                            "variables": {
                                "date": show_date.isoformat(),
                                "siteIds": [MCKINNEY_SITE_ID],
                            },
                            "siteId": MCKINNEY_SITE_ID,
                            "circuitId": CINEPOLIS_CIRCUIT_ID,
                        },
                    )
                finally:
                    browser.close()

            if result["status"] != 200:
                raise RuntimeError(f"GraphQL request failed with HTTP {result['status']}")

            payload = json.loads(result["text"])
            if payload.get("errors"):
                raise RuntimeError(f"GraphQL request returned errors: {payload['errors']}")

            return payload["data"]["showingsForDate"]
        except (PlaywrightError, BlockedError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "Fetch attempt %d/%d failed for %s: %s",
                attempt, MAX_FETCH_ATTEMPTS, source_url, exc,
            )
            if attempt < MAX_FETCH_ATTEMPTS:
                time_module.sleep(RETRY_BACKOFF_SECONDS)

    assert last_error is not None
    raise last_error


def parse_showings_response(showings_response: dict[str, Any]) -> list[ScrapedShowtime]:
    """Map a `showingsForDate` GraphQL response into showtime records.

    NOTE: This query does not return an explicit format/auditorium label
    (e.g. "Standard"/"4DX"/"VIP") - only a `screenId`. Resolving that to a
    human-readable format would require a separate screens/auditoriums
    lookup that wasn't needed to get real showtime data working for this
    alpha pilot, so `format` is left `None` for now (the data model and
    FR-003 already treat format as optional/nullable).
    """
    showtimes: list[ScrapedShowtime] = []

    for entry in showings_response.get("data", []):
        movie = entry.get("movie") or {}
        movie_title = (movie.get("name") or "").strip()
        raw_time = entry.get("time")
        if not movie_title or not raw_time:
            continue

        try:
            parsed_utc = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(
                "Skipping showing with unparseable time %r for %r", raw_time, movie_title
            )
            continue

        local_dt = parsed_utc.astimezone(CENTRAL_TIME)
        showtimes.append(
            ScrapedShowtime(
                movie_title=movie_title,
                show_date=local_dt.date(),
                start_time=local_dt.time(),
                format=None,
            )
        )

    return showtimes


def scrape_showtimes(source_url: str, show_date: date | None = None) -> list[ScrapedShowtime]:
    show_date = show_date or datetime.now(tz=CENTRAL_TIME).date()
    showings_response = fetch_showings_json(source_url, show_date)
    return parse_showings_response(showings_response)
