import json
import logging
import re
import time as time_module
from datetime import date, datetime, time
from typing import Any, NamedTuple
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
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

# Cinepolis' GraphQL API exposes no ticket/booking URL field at all (schema
# probed directly; introspection is disabled in production). This template
# was instead confirmed by observing the site's real "buy tickets" flow in
# a live browser: clicking a showing navigates to exactly this URL, where
# {id} is the same showing id already present in every showingsForDate
# response entry. No extra network call is needed to build it. Undocumented
# client route, same risk category as the GraphQL API itself — see
# research.md.
TICKET_URL_TEMPLATE = "https://www.cinepolisusa.com/mckinney/checkout/seats/{id}"

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
    ticket_url: str | None


class ScrapeResult(NamedTuple):
    showtimes: list[ScrapedShowtime]
    # The GraphQL response's own `count` of showings, vs. len(showtimes)
    # after parsing: a discrepancy means some entries were skipped (missing
    # movie name / unparseable time — see parse_showings_response) rather
    # than genuinely absent from the source, distinguishing a "partial"
    # ingestion run from a clean "success".
    reported_count: int


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

        showing_id = entry.get("id")
        ticket_url = TICKET_URL_TEMPLATE.format(id=showing_id) if showing_id else None

        local_dt = parsed_utc.astimezone(CENTRAL_TIME)
        showtimes.append(
            ScrapedShowtime(
                movie_title=movie_title,
                show_date=local_dt.date(),
                start_time=local_dt.time(),
                format=None,
                ticket_url=ticket_url,
            )
        )

    return showtimes


def scrape_showtimes(source_url: str, show_date: date | None = None) -> ScrapeResult:
    show_date = show_date or datetime.now(tz=CENTRAL_TIME).date()
    showings_response = fetch_showings_json(source_url, show_date)
    showtimes = parse_showings_response(showings_response)
    reported_count = showings_response.get("count", len(showtimes))
    return ScrapeResult(showtimes=showtimes, reported_count=reported_count)


# --- Texas Theatre Showtime Source Scraper ---

FORMAT_PATTERNS = [
    (re.compile(r"\b35mm\b", re.IGNORECASE), "35mm"),
    (re.compile(r"\b70mm\b", re.IGNORECASE), "70mm"),
    (re.compile(r"\b16mm\b", re.IGNORECASE), "16mm"),
    (re.compile(r"\b4k\b", re.IGNORECASE), "4K"),
    (re.compile(r"\b(dcp|digital)\b", re.IGNORECASE), "Digital"),
]


def extract_format(text: str) -> str | None:
    if not text:
        return None
    for pattern, fmt_label in FORMAT_PATTERNS:
        if pattern.search(text):
            return fmt_label
    return None


# Non-film venue events the Texas Theatre calendar also lists alongside film
# screenings (spec FR-008, Edge Cases, Assumptions) — excluded so they don't
# pollute movie-recommendation data with non-movie titles.
NON_FILM_EVENT_KEYWORDS = re.compile(
    r"\b("
    r"live music|concert|comedy|stand-?up|karaoke|trivia|drag show|burlesque|"
    r"book club|lecture|panel discussion|live podcast|open mic|dj set|"
    r"music video showcase"
    r")\b",
    re.IGNORECASE,
)


def is_non_film_event(text: str) -> bool:
    if not text:
        return False
    return bool(NON_FILM_EVENT_KEYWORDS.search(text))


MONTH_NUMBERS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _extract_calendar_year(soup: BeautifulSoup) -> int:
    """The calendar page's <title> is "<Month> <Year> | The Texas Theatre"
    (e.g. "July 2026 | The Texas Theatre") — the per-listing date text
    itself never includes a year, so this is the only source for one."""
    title = soup.find("title")
    if title:
        match = re.search(r"(\d{4})", title.get_text())
        if match:
            return int(match.group(1))
    return datetime.now(tz=CENTRAL_TIME).year


def _parse_listing_date(text: str, year: int) -> date | None:
    match = re.search(r"([A-Za-z]{3,9})\s+(\d{1,2})", text)
    if not match:
        return None
    month = MONTH_NUMBERS.get(match.group(1).lower()[:3])
    if month is None:
        return None
    try:
        return date(year, month, int(match.group(2)))
    except ValueError:
        return None


def _parse_listing_time(text: str) -> time | None:
    match = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", text, re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    ampm = (match.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    try:
        return time(hour, minute)
    except ValueError:
        return None


def parse_texas_theatre_html(
    html: str, base_url: str = "https://thetexastheatre.com"
) -> tuple[list[ScrapedShowtime], int]:
    """Parse the Texas Theatre calendar page's server-rendered markup.

    Each film gets one `div.calendar-listing` block: one title, one show
    date, and one or more showtimes — each showtime is its own `<li>`
    with its own ticket link and (usually) its own `.film-format` span,
    since the same film can screen in different formats across its run.
    Non-film venue events are excluded (spec FR-008) via a `.tags span`
    class that doesn't contain "film", combined with a keyword heuristic
    that also runs on tagged listings (the site's own "film_and_event"
    tag isn't reliable alone — verified live against a listing tagged
    that way despite being a pure "Music Video Showcase"). Excluded
    listings are skipped before being counted at all, so they never
    trigger a false "partial" outcome in ingest.py.
    """
    soup = BeautifulSoup(html, "html.parser")
    year = _extract_calendar_year(soup)

    showtimes: list[ScrapedShowtime] = []
    reported_count = 0

    for listing in soup.select("div.calendar-listing"):
        listing_text = listing.get_text(" ", strip=True)

        tag_span = listing.select_one(".tags span")
        if tag_span is not None:
            classes = tag_span.get("class") or [""]
            if "film" not in classes[0].lower():
                continue  # a non-film-only venue event (e.g. live music, comedy)

        # The site's own "film_and_event" tag is not reliable on its own —
        # confirmed live against a "Davis & Pellington Music Video
        # Showcase" listing tagged "film_and_event" despite not being a
        # film at all — so the keyword heuristic runs unconditionally,
        # not just as a fallback for untagged listings.
        if is_non_film_event(listing_text):
            continue

        title_el = listing.select_one("h3 a")
        title = title_el.get_text(" ", strip=True) if title_el else ""

        date_el = listing.select_one(".listing-showtimes .visually-hidden")
        show_date = _parse_listing_date(date_el.get_text(strip=True), year) if date_el else None

        listing_format_fallback = extract_format(listing_text)

        for li in listing.select("ul.times li"):
            reported_count += 1
            link = li.find("a")
            if link is None:
                continue

            start_time = _parse_listing_time(link.get_text(strip=True))

            href = (link.get("href") or "").strip()
            # urljoin (not naive string concat) since base_url is the
            # /calendar page itself — a root-relative href like
            # "/order/add-tickets/2016/nojs" must resolve against the
            # site origin, not get appended onto "/calendar" too.
            ticket_url = urljoin(base_url, href) if href else None

            format_el = li.select_one(".film-format")
            fmt = format_el.get_text(strip=True) if format_el else listing_format_fallback

            if title and show_date and start_time:
                showtimes.append(
                    ScrapedShowtime(
                        movie_title=title,
                        show_date=show_date,
                        start_time=start_time,
                        format=fmt or None,
                        ticket_url=ticket_url,
                    )
                )

    return showtimes, reported_count


def fetch_texas_theatre_html(source_url: str, timeout_ms: int = 30_000) -> str:
    last_error: Exception | None = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=REALISTIC_USER_AGENT)
                Stealth().apply_stealth_sync(context)
                page = context.new_page()
                page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                html = page.content()
                browser.close()

                if looks_blocked(html):
                    raise BlockedError(f"Blocked by bot protection for {source_url}")
                return html
        except (PlaywrightError, BlockedError, RuntimeError) as exc:
            last_error = exc
            logger.warning(
                "Fetch attempt %d/%d failed for %s: %s",
                attempt, MAX_FETCH_ATTEMPTS, source_url, exc,
            )
            if attempt < MAX_FETCH_ATTEMPTS:
                time_module.sleep(RETRY_BACKOFF_SECONDS)

    assert last_error is not None
    raise last_error


def scrape_texas_theatre_showtimes(
    source_url: str = "https://thetexastheatre.com/calendar"
) -> ScrapeResult:
    logger.info("Starting Texas Theatre showtime scrape for %s", source_url)
    html = fetch_texas_theatre_html(source_url)
    showtimes, reported_count = parse_texas_theatre_html(html, base_url=source_url)
    logger.info(
        "Texas Theatre scrape complete: %d showtime(s) parsed out of %d reported events",
        len(showtimes), reported_count,
    )
    return ScrapeResult(showtimes=showtimes, reported_count=reported_count)

