import json
import logging
import re
import time as time_module
from datetime import date, datetime, time, timedelta
from typing import Any, Callable, NamedTuple
from urllib.parse import parse_qs, urljoin, urlsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

MAX_FETCH_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5

# How many consecutive empty periods (dates for Cinepolis, months for Texas
# Theatre) to see before concluding a source's published calendar has ended,
# rather than stopping on the first empty one — Texas Theatre's real
# calendar was observed to taper non-monotonically (research.md §2: a
# 4-listing month followed by a 5-listing month), so a single empty period
# is not a safe stop condition on its own.
MAX_CONSECUTIVE_EMPTY_PERIODS = 2

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
    # Whether the fetch walked all the way to the source's own end of its
    # published calendar (per-source stop condition) before returning,
    # vs. stopping early because a request failed after exhausting
    # retries. `run_ingestion` must only mark previously-active showtimes
    # stale when this is True — otherwise a showtime that simply wasn't
    # reached yet would be wrongly treated as no longer published.
    complete: bool = True
    # Set when complete=False: identifies which page/date/month the walk
    # was on when it gave up, so the recorded IngestionRun.error_message
    # is actionable from container logs alone (Constitution V).
    incomplete_reason: str | None = None


class BlockedError(RuntimeError):
    """Raised when the source appears to have served a bot-protection
    challenge/block page instead of real content."""


def looks_blocked(html: str) -> bool:
    return any(marker in html for marker in BLOCK_PAGE_MARKERS)


def _query_showings_for_date_json(page: Any, show_date: date) -> dict[str, Any]:
    """Run one `showingsForDate` GraphQL query from within an already-loaded,
    already-authorized Cinepolis page's own JS context (see
    `scrape_showtimes` for why it must be `page.evaluate`, not a separate
    HTTP client). No retry/browser-launch here — callers reusing one page
    across many dates handle retries per date via
    `_query_showings_for_date_with_retry`."""
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

    if result["status"] != 200:
        raise RuntimeError(f"GraphQL request failed with HTTP {result['status']}")

    payload = json.loads(result["text"])
    if payload.get("errors"):
        raise RuntimeError(f"GraphQL request returned errors: {payload['errors']}")

    return payload["data"]["showingsForDate"]


def _query_showings_for_date_with_retry(page: Any, show_date: date) -> dict[str, Any]:
    """Transient failures (timeouts, block pages mid-session) are retried a
    few times with a short backoff before giving up on this one date."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            if looks_blocked(page.content()):
                raise BlockedError("Source appears to have served a block/challenge page")
            return _query_showings_for_date_json(page, show_date)
        except (PlaywrightError, BlockedError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            logger.warning(
                "Fetch attempt %d/%d failed for %s: %s",
                attempt, MAX_FETCH_ATTEMPTS, show_date.isoformat(), exc,
            )
            if attempt < MAX_FETCH_ATTEMPTS:
                time_module.sleep(RETRY_BACKOFF_SECONDS)

    assert last_error is not None
    raise last_error


def fetch_showings_json(
    source_url: str, show_date: date, timeout_ms: int = 30_000
) -> dict[str, Any]:
    """Fetch raw showtime data for a single date from Cinepolis' GraphQL
    API, launching a fresh browser/page for just this one date.

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

    Kept as a standalone single-date helper (used internally by
    `scrape_showtimes` for its first date, and available for one-off
    lookups); fetching multiple dates in one run reuses one browser/page
    instead of calling this repeatedly — see `scrape_showtimes`.
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

                    return _query_showings_for_date_json(page, show_date)
                finally:
                    browser.close()
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


def _walk_cinepolis_dates(
    query_date_fn: Callable[[date], dict[str, Any]],
    start_date: date,
    max_consecutive_empty: int = MAX_CONSECUTIVE_EMPTY_PERIODS,
) -> ScrapeResult:
    """Walk forward one date at a time from `start_date`, calling
    `query_date_fn(d)` for each (already retried internally — see
    `_query_showings_for_date_with_retry`), until `max_consecutive_empty`
    consecutive dates report zero showings (research.md §1) or a query
    raises after exhausting its own retries.

    Pure walking/stop-condition logic, independent of Playwright, so it
    can be unit tested with a fake `query_date_fn`.
    """
    showtimes: list[ScrapedShowtime] = []
    reported_count = 0
    consecutive_empty = 0
    current_date = start_date
    complete = False
    incomplete_reason: str | None = None

    while True:
        try:
            showings_response = query_date_fn(current_date)
        except Exception as exc:  # noqa: BLE001 - any per-date failure ends the walk, not the run
            incomplete_reason = f"failed fetching {current_date.isoformat()}: {exc}"
            break

        day_showtimes = parse_showings_response(showings_response)
        day_count = showings_response.get("count", len(day_showtimes))
        reported_count += day_count
        showtimes.extend(day_showtimes)

        if day_count == 0:
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                complete = True
                break
        else:
            consecutive_empty = 0

        current_date += timedelta(days=1)

    return ScrapeResult(
        showtimes=showtimes,
        reported_count=reported_count,
        complete=complete,
        incomplete_reason=incomplete_reason,
    )


def scrape_showtimes(source_url: str, start_date: date | None = None) -> ScrapeResult:
    """Fetch every showtime Cinepolis currently has published, starting
    from `start_date` (defaults to today).

    One browser/page is launched and authorized against Cloudflare once
    for the whole run, then reused for one `page.evaluate` GraphQL call
    per date (research.md §1) — relaunching a browser per date would
    multiply both run time and Cloudflare-challenge exposure roughly
    linearly with the number of dates fetched.
    """
    start_date = start_date or datetime.now(tz=CENTRAL_TIME).date()
    logger.info("Starting Cinepolis showtime scrape for %s from %s", source_url, start_date)

    with Stealth().use_sync(sync_playwright()) as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(
                user_agent=REALISTIC_USER_AGENT,
                viewport={"width": 1920, "height": 1080},
            )
            page.goto(source_url, timeout=30_000, wait_until="networkidle")

            if looks_blocked(page.content()):
                raise BlockedError(
                    f"Source appears to have served a block/challenge page: {source_url}"
                )

            result = _walk_cinepolis_dates(
                lambda d: _query_showings_for_date_with_retry(page, d), start_date
            )
        finally:
            browser.close()

    logger.info(
        "Cinepolis scrape complete: %d showtime(s) parsed out of %d reported (complete=%s)",
        len(result.showtimes), result.reported_count, result.complete,
    )
    return result


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


def _fetch_page_html_with_retry(page: Any, url: str, timeout_ms: int = 30_000) -> str:
    """Fetch one calendar page's HTML from an already-open Playwright
    `page`/context, retrying transient failures a few times with a short
    backoff before giving up on this one page."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            html = page.content()
            if looks_blocked(html):
                raise BlockedError(f"Blocked by bot protection for {url}")
            return html
        except (PlaywrightError, BlockedError, RuntimeError) as exc:
            last_error = exc
            logger.warning(
                "Fetch attempt %d/%d failed for %s: %s",
                attempt, MAX_FETCH_ATTEMPTS, url, exc,
            )
            if attempt < MAX_FETCH_ATTEMPTS:
                time_module.sleep(RETRY_BACKOFF_SECONDS)

    assert last_error is not None
    raise last_error


def fetch_texas_theatre_html(source_url: str, timeout_ms: int = 30_000) -> str:
    """Fetch a single calendar page's HTML, launching its own browser/
    context. Kept as a standalone single-page helper (available for
    one-off lookups); fetching a source's full calendar reuses one
    browser/context across months instead of calling this repeatedly —
    see `scrape_texas_theatre_showtimes`."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=REALISTIC_USER_AGENT)
            Stealth().apply_stealth_sync(context)
            page = context.new_page()
            return _fetch_page_html_with_retry(page, source_url, timeout_ms)
        finally:
            browser.close()


def extract_next_month_url(html: str, base_url: str) -> str | None:
    """The calendar page's own "next month" link — `a.calendar-next`,
    confirmed live against thetexastheatre.com/calendar (research.md §2)
    — is authoritative for "what comes after this month," rather than
    guessing at a `/calendar/<month>/<year>` URL scheme by hand."""
    soup = BeautifulSoup(html, "html.parser")
    next_link = soup.select_one("a.calendar-next")
    if next_link is None:
        return None
    href = (next_link.get("href") or "").strip()
    return urljoin(base_url, href) if href else None


def _walk_texas_theatre_months(
    fetch_page_fn: Callable[[str], str],
    start_url: str,
    base_url: str,
    max_consecutive_empty: int = MAX_CONSECUTIVE_EMPTY_PERIODS,
) -> ScrapeResult:
    """Walk forward one calendar month page at a time from `start_url`,
    following each page's own "next month" link, until
    `max_consecutive_empty` consecutive months report zero listings
    (research.md §2 — a single empty month is not a safe stop condition,
    since real listing counts taper non-monotonically) or a page fetch
    raises after exhausting its own retries, or the site stops providing
    a "next month" link at all.

    Pure walking/stop-condition logic, independent of Playwright, so it
    can be unit tested with a fake `fetch_page_fn`.
    """
    showtimes: list[ScrapedShowtime] = []
    reported_count = 0
    consecutive_empty = 0
    current_url = start_url
    visited: set[str] = set()
    complete = False
    incomplete_reason: str | None = None

    while True:
        if current_url in visited:
            # Defensive guard against a "next month" link cycle; the site
            # has always advanced forward in practice (research.md §2).
            complete = True
            break
        visited.add(current_url)

        try:
            html = fetch_page_fn(current_url)
        except Exception as exc:  # noqa: BLE001 - any per-page failure ends the walk, not the run
            incomplete_reason = f"failed fetching {current_url}: {exc}"
            break

        month_showtimes, month_count = parse_texas_theatre_html(html, base_url=base_url)
        showtimes.extend(month_showtimes)
        reported_count += month_count

        if month_count == 0:
            consecutive_empty += 1
            if consecutive_empty >= max_consecutive_empty:
                complete = True
                break
        else:
            consecutive_empty = 0

        next_url = extract_next_month_url(html, base_url)
        if next_url is None:
            complete = True
            break
        current_url = next_url

    return ScrapeResult(
        showtimes=showtimes,
        reported_count=reported_count,
        complete=complete,
        incomplete_reason=incomplete_reason,
    )


def scrape_texas_theatre_showtimes(
    source_url: str = "https://thetexastheatre.com/calendar"
) -> ScrapeResult:
    """Fetch every showtime Texas Theatre currently has published,
    starting from the current month's calendar page and walking forward
    (research.md §2). One browser/context/page is reused across all
    months fetched in this run."""
    logger.info("Starting Texas Theatre showtime scrape for %s", source_url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=REALISTIC_USER_AGENT)
            Stealth().apply_stealth_sync(context)
            page = context.new_page()
            result = _walk_texas_theatre_months(
                lambda url: _fetch_page_html_with_retry(page, url),
                source_url,
                base_url=source_url,
            )
        finally:
            browser.close()

    logger.info(
        "Texas Theatre scrape complete: %d showtime(s) parsed out of %d reported events "
        "across the walked calendar (complete=%s)",
        len(result.showtimes), result.reported_count, result.complete,
    )
    return result


# --- Angelika Film Center Dallas Showtime Source Scraper ---

# Angelika Film Center Dallas is one brand on Reading Cinemas' shared multi-brand
# React SPA/booking platform (also serves readingcinemas.com and
# consolidatedtheatres.com). The site's own page has no server-rendered showtime
# markup — it fetches everything from a JSON API at production-api.readingcinemas.com,
# gated by a WAF/CORS policy that rejects hand-crafted requests (plain curl and even
# a same-page injected fetch() both get rejected, unlike Cinepolis' GraphQL API which
# only needed two custom headers). Rather than reverse-engineer that auth scheme, this
# fetch lets the real page load normally and captures the *response* to its own
# authenticated request via Playwright's network layer (page.expect_response), which
# is unaffected by the page-script CORS restrictions that blocked a replayed request.
# cinemaId, endpoint, and response shape below were confirmed by inspecting live
# network traffic against https://angelikafilmcenter.com/dallas (see research.md §1).
#
# The `/films` response is per-date, not full-window — live capture (research.md
# §3, superseding an earlier incorrect assumption) confirmed the request always
# carries a `selectedDate` query param, and clicking a different date on the
# "now playing" page's own date-selector strip re-issues the request with that
# date. The strip itself (`div#anytime > span`, one per selectable date) is the
# site's own authoritative, already-computed list of every date it currently has
# showtimes for — walking exactly those dates (one click + capture per date,
# after the first, which the initial page load already captures) gives the full
# published window with no guessing at a stop condition.
ANGELIKA_DALLAS_CINEMA_ID = "0000000009"

_ANGELIKA_DATE_STRIP_SELECTOR = "#anytime span"
_ANGELIKA_DATE_LABEL_RE = re.compile(r"(\d{1,2})/(\d{1,2})$")

# Confirmed via the site's own client-side router (route pattern
# "/cinemas/:cinemaId/sessions/:sessionId/:movieId"); the films API response includes
# no ticket URL field directly, so this is built from the session's own `id` and the
# movie's numeric `slug`, both already present in every showtime entry.
ANGELIKA_TICKET_URL_TEMPLATE = (
    f"https://angelikafilmcenter.com/cinemas/{ANGELIKA_DALLAS_CINEMA_ID}"
    "/sessions/{session_id}/{movie_slug}"
)

# The API's date_time field (e.g. "2026-07-23T09:00:00-05") carries a UTC offset with
# no minutes component, which datetime.fromisoformat() rejects; normalize it to
# "-05:00" before parsing.
_ANGELIKA_OFFSET_FIX = re.compile(r"([+-]\d{2})$")


def _parse_angelika_datetime(raw_date_time: str) -> datetime | None:
    normalized = _ANGELIKA_OFFSET_FIX.sub(r"\1:00", raw_date_time)
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        logger.warning(
            "Skipping Angelika Dallas showtime with unparseable date_time %r", raw_date_time
        )
        return None


def fetch_angelika_dallas_films(
    source_url: str = "https://angelikafilmcenter.com/dallas", timeout_ms: int = 30_000
) -> dict[str, Any]:
    """Load the Angelika Dallas page and capture the JSON response its own
    front-end receives from the `/films` showtimes API, rather than replaying
    the request ourselves (see module-level comment above)."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context(user_agent=REALISTIC_USER_AGENT)
                    Stealth().apply_stealth_sync(context)
                    page = context.new_page()
                    try:
                        with page.expect_response(
                            lambda response: "/films" in response.url
                            and f"cinemaId={ANGELIKA_DALLAS_CINEMA_ID}" in response.url,
                            timeout=timeout_ms,
                        ) as response_info:
                            page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    except PlaywrightTimeoutError as exc:
                        if looks_blocked(page.content()):
                            raise BlockedError(
                                "Source appears to have served a block/challenge page: "
                                f"{source_url}"
                            ) from exc
                        raise

                    response = response_info.value
                    if response.status != 200:
                        raise RuntimeError(
                            f"Angelika Dallas films request failed with HTTP {response.status}"
                        )
                    return response.json()
                finally:
                    browser.close()
        except (PlaywrightError, PlaywrightTimeoutError, BlockedError, RuntimeError) as exc:
            last_error = exc
            logger.warning(
                "Fetch attempt %d/%d failed for %s: %s",
                attempt, MAX_FETCH_ATTEMPTS, source_url, exc,
            )
            if attempt < MAX_FETCH_ATTEMPTS:
                time_module.sleep(RETRY_BACKOFF_SECONDS)

    assert last_error is not None
    raise last_error


def _parse_angelika_date_strip_label(label: str, today: date) -> date | None:
    """Labels are like "Today, 7/23", "Tomorrow, 7/24", "Sunday 7/26" —
    always month/day with no year. The strip only ever runs forward from
    today, so a month/day earlier in the calendar than today belongs to
    next year."""
    match = _ANGELIKA_DATE_LABEL_RE.search(label)
    if not match:
        return None
    month, day = int(match.group(1)), int(match.group(2))
    try:
        candidate = date(today.year, month, day)
    except ValueError:
        return None
    if candidate < today:
        try:
            candidate = date(today.year + 1, month, day)
        except ValueError:
            return None
    return candidate


def _extract_angelika_labeled_dates(page: Any, today: date) -> list[tuple[str, date]]:
    """Read the "now playing" date-selector strip's own declared list of
    bookable dates straight from the DOM (research.md §3) — the site's
    own already-computed full booking horizon for currently-open movies,
    rather than a guessed stop condition or URL pagination scheme."""
    labels = page.eval_on_selector_all(
        _ANGELIKA_DATE_STRIP_SELECTOR, "nodes => nodes.map(n => n.textContent.trim())"
    )
    labeled_dates = []
    for label in labels:
        parsed = _parse_angelika_date_strip_label(label, today)
        if parsed is not None:
            labeled_dates.append((label, parsed))
    return labeled_dates


def _click_angelika_date_with_retry(
    page: Any, label: str, timeout_ms: int = 30_000
) -> dict[str, Any]:
    """Click one date-strip button and capture the `/films` response it
    triggers, retrying transient failures a few times with a short
    backoff before giving up on this one date."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with page.expect_response(
                lambda response: "/films" in response.url
                and f"cinemaId={ANGELIKA_DALLAS_CINEMA_ID}" in response.url,
                timeout=timeout_ms,
            ) as response_info:
                page.get_by_text(label, exact=True).first.click(timeout=timeout_ms)
            response = response_info.value
            if response.status != 200:
                raise RuntimeError(
                    f"Angelika Dallas films request failed with HTTP {response.status} "
                    f"for date {label!r}"
                )
            return response.json()
        except (PlaywrightError, PlaywrightTimeoutError, RuntimeError) as exc:
            last_error = exc
            logger.warning(
                "Fetch attempt %d/%d failed for date %s: %s",
                attempt, MAX_FETCH_ATTEMPTS, label, exc,
            )
            if attempt < MAX_FETCH_ATTEMPTS:
                time_module.sleep(RETRY_BACKOFF_SECONDS)

    assert last_error is not None
    raise last_error


def _walk_angelika_dallas_dates(
    labeled_dates: list[tuple[str, date]],
    initial_payload: dict[str, Any],
    query_label_fn: Callable[[str], dict[str, Any]],
) -> ScrapeResult:
    """Fold the already-captured initial page load's payload (covering
    `labeled_dates[0]`, "today") together with one `query_label_fn(label)`
    call per remaining labeled date (each already retried internally),
    stopping early if a date's fetch raises after exhausting its own
    retries. Complete only when every labeled date was fetched.

    Pure walking logic, independent of Playwright, so it can be unit
    tested with a fake `query_label_fn`.
    """
    if not labeled_dates:
        return ScrapeResult(showtimes=[], reported_count=0, complete=True)

    payloads = [initial_payload]
    complete = False
    incomplete_reason: str | None = None

    for label, _ in labeled_dates[1:]:
        try:
            payloads.append(query_label_fn(label))
        except Exception as exc:  # noqa: BLE001 - any per-date failure ends the walk, not the run
            incomplete_reason = f"failed fetching {label}: {exc}"
            break
    else:
        complete = True

    showtimes: list[ScrapedShowtime] = []
    reported_count = 0
    for payload in payloads:
        day_showtimes, day_count = parse_angelika_dallas_films(payload)
        showtimes.extend(day_showtimes)
        reported_count += day_count

    return ScrapeResult(
        showtimes=showtimes,
        reported_count=reported_count,
        complete=complete,
        incomplete_reason=incomplete_reason,
    )


def parse_angelika_dallas_films(payload: dict[str, Any]) -> tuple[list[ScrapedShowtime], int]:
    """Map a `/films` API response into showtime records.

    The endpoint returns films only (no non-film venue events mixed in, unlike
    Texas Theatre's calendar), so no non-film classification/filtering is
    needed here (spec FR-008 is satisfied by the source itself).
    """
    showtimes: list[ScrapedShowtime] = []
    reported_count = 0

    movies = payload.get("nowShowing", {}).get("data", {}).get("movies", [])

    for movie in movies:
        title = (movie.get("name") or "").strip()
        movie_slug = movie.get("slug")

        for showdate in movie.get("showdates", []):
            for showtype in showdate.get("showtypes", []):
                fmt = (showtype.get("type") or "").strip() or None

                for session in showtype.get("showtimes", []):
                    reported_count += 1

                    raw_date_time = session.get("date_time")
                    parsed = _parse_angelika_datetime(raw_date_time) if raw_date_time else None
                    if not title or parsed is None:
                        continue

                    session_id = session.get("id")
                    ticket_url = (
                        ANGELIKA_TICKET_URL_TEMPLATE.format(
                            session_id=session_id, movie_slug=movie_slug
                        )
                        if session_id and movie_slug
                        else None
                    )

                    showtimes.append(
                        ScrapedShowtime(
                            movie_title=title,
                            show_date=parsed.date(),
                            start_time=parsed.time(),
                            format=fmt,
                            ticket_url=ticket_url,
                        )
                    )

    return showtimes, reported_count


def scrape_angelika_dallas_showtimes(
    source_url: str = "https://angelikafilmcenter.com/dallas", timeout_ms: int = 30_000
) -> ScrapeResult:
    """Fetch every showtime Angelika Dallas currently has published for
    its already-open movies, across every date its own "now playing"
    date-selector strip currently offers (research.md §3) — not just
    today. One browser/context/page is reused across all dates clicked
    through in this run."""
    logger.info("Starting Angelika Dallas showtime scrape for %s", source_url)
    today = datetime.now(tz=CENTRAL_TIME).date()

    last_error: Exception | None = None
    for attempt in range(1, MAX_FETCH_ATTEMPTS + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context(user_agent=REALISTIC_USER_AGENT)
                    Stealth().apply_stealth_sync(context)
                    page = context.new_page()
                    try:
                        with page.expect_response(
                            lambda response: "/films" in response.url
                            and f"cinemaId={ANGELIKA_DALLAS_CINEMA_ID}" in response.url,
                            timeout=timeout_ms,
                        ) as response_info:
                            page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    except PlaywrightTimeoutError as exc:
                        if looks_blocked(page.content()):
                            raise BlockedError(
                                "Source appears to have served a block/challenge page: "
                                f"{source_url}"
                            ) from exc
                        raise

                    initial_response = response_info.value
                    if initial_response.status != 200:
                        raise RuntimeError(
                            "Angelika Dallas films request failed with HTTP "
                            f"{initial_response.status}"
                        )
                    initial_payload = initial_response.json()

                    labeled_dates = _extract_angelika_labeled_dates(page, today)
                    result = _walk_angelika_dallas_dates(
                        labeled_dates,
                        initial_payload,
                        lambda label: _click_angelika_date_with_retry(page, label, timeout_ms),
                    )
                finally:
                    browser.close()
        except (
            PlaywrightError, PlaywrightTimeoutError, BlockedError,
            RuntimeError, json.JSONDecodeError,
        ) as exc:
            last_error = exc
            logger.warning(
                "Fetch attempt %d/%d failed for %s: %s",
                attempt, MAX_FETCH_ATTEMPTS, source_url, exc,
            )
            if attempt < MAX_FETCH_ATTEMPTS:
                time_module.sleep(RETRY_BACKOFF_SECONDS)
                continue
            raise
        else:
            logger.info(
                "Angelika Dallas scrape complete: %d showtime(s) parsed out of %d reported "
                "sessions across %d date(s) (complete=%s)",
                len(result.showtimes), result.reported_count, len(labeled_dates), result.complete,
            )
            return result

    assert last_error is not None
    raise last_error


# --- Cinemark West Plano XD and ScreenX Showtime Source Scraper ---

# Cinemark West Plano's date-tab widget is backed by a first-party,
# server-rendered Umbraco "surface controller" endpoint — confirmed by
# inspecting live network traffic against
# https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx
# (spec 012 research.md §1): clicking a date tab issues
# GET /umbraco/surface/Showtimes/GetByTheaterId?theaterId=231&showDate=YYYY-MM-DD
# and swaps in the returned HTML. Unlike Angelika Dallas, no client JSON API
# or auth scheme needs to be reverse-engineered — the endpoint itself
# returns real showtime markup, fetched the same way as Texas Theatre's
# calendar pages (Playwright + stealth, retried via
# `_fetch_page_html_with_retry`), since plain-httpx behavior against this
# endpoint hasn't been verified headless (research.md §1).
#
# 70mm presentations are NOT a format tag on the base film's listing — they
# appear as an entirely separate movie listing whose title ends in " 70mm"
# and which carries its own CinemarkMovieId (confirmed live: "The Odyssey"
# id=108919 vs. "The Odyssey 70mm" id=110535). The parser strips that title
# suffix and tags format="70mm" instead, so 70mm showtimes fold back into
# the base film's identity rather than surfacing as a separate "movie"
# (research.md §2).
CINEMARK_WEST_PLANO_THEATER_ID = "231"

_CINEMARK_70MM_TITLE_RE = re.compile(r"\s+70mm$", re.IGNORECASE)
_CINEMARK_DATEVALUE_RE = re.compile(r'data-datevalue="(\d{4}-\d{2}-\d{2})"')
_CINEMARK_MOVIE_BLOCK_SELECTOR = 'div[class*="showtimeMovieBlock"]'


def extract_cinemark_west_plano_dates(html: str) -> list[date]:
    """The theatre page's own date-tab strip (`a.showdate-link
    [data-datevalue="YYYY-MM-DD"]`) is the site's authoritative list of
    every date it currently has a schedule for (research.md §4) — walked
    in document order and deduplicated, rather than guessing a fixed day
    count."""
    seen: set[str] = set()
    dates: list[date] = []
    for raw in _CINEMARK_DATEVALUE_RE.findall(html):
        if raw in seen:
            continue
        seen.add(raw)
        try:
            dates.append(date.fromisoformat(raw))
        except ValueError:
            continue
    return dates


def _strip_cinemark_70mm_suffix(title: str) -> tuple[str, bool]:
    match = _CINEMARK_70MM_TITLE_RE.search(title)
    if not match:
        return title, False
    return title[: match.start()].strip(), True


def _cinemark_format_badge_text(alt: str) -> str:
    """Badge alt text like "Cinemark XD" carries a "Cinemark " prefix not
    present on the D-BOX/ScreenX/RealD 3D badges; strip it for a
    consistent bare format label (research.md §2)."""
    alt = alt.strip()
    if alt.lower().startswith("cinemark "):
        return alt[len("cinemark "):].strip()
    return alt


def _extract_cinemark_group_format(attribute_list_ul: Any) -> str | None:
    """One `ul.attribute-list--auditorium-attributes` group can carry more
    than one format badge at once (e.g. XD + D-BOX together, confirmed
    live) — all badges present are joined into one deterministic value
    rather than only taking the first (research.md §2, spec FR-010). A
    group with no badge falls back to its own plain-text label (e.g.
    "Standard Format" -> "Standard"); a group with both a badge and a
    "Standard Format" text label (e.g. "D-BOX" showtimes that are
    otherwise the standard, non-XD/non-70mm presentation) is tagged by
    its badge alone, since the badge is the more specific signal."""
    badges = [
        _cinemark_format_badge_text(img.get("alt") or "")
        for img in attribute_list_ul.find_all("img")
        if (img.get("alt") or "").strip()
    ]
    if badges:
        return "+".join(badges)

    text_el = attribute_list_ul.find("li", class_="attribute-list__item--text")
    if text_el is not None:
        text = text_el.get_text(strip=True)
        if text.lower() == "standard format":
            return "Standard"
        return text or None
    return None


def _parse_cinemark_ticket_url_showtime(href: str) -> datetime | None:
    """Each showtime's own `TicketSeatMap` link carries a `Showtime=`
    query param with a naive local (Central Time) ISO timestamp — the
    same value displayed on the page, confirmed live (research.md §3/§5)
    — so no separate URL construction or offset handling is needed."""
    raw = parse_qs(urlsplit(href).query).get("Showtime", [None])[0]
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def parse_cinemark_west_plano_html(
    html: str, base_url: str = "https://www.cinemark.com"
) -> tuple[list[ScrapedShowtime], int]:
    """Parse one date's `GetByTheaterId` HTML fragment.

    Each film gets one `div[class*="showtimeMovieBlock"]` block. Within
    it, `.movieBlockShowtimes` holds a flat, repeating sequence of direct
    children in document order: a `ul.attribute-list--auditorium-
    attributes` (the current format group's badges/label) followed by one
    or more `div.showtimeMovieTimes` blocks (a "Late Fri Night/Sat
    Morning" secondary time block can appear with no attribute-list of
    its own — confirmed live: 3 attribute-list groups but 4
    showtimeMovieTimes blocks for a single film) — so groups are tracked
    by walking DOM order and remembering the most recently seen
    attribute-list, not by zipping parallel lists.

    Non-film venue events: no distinguishing signal was found in this
    markup during research (research.md §6); every listing is treated as
    a film screening, matching the spec's Assumptions section.
    """
    soup = BeautifulSoup(html, "html.parser")
    showtimes: list[ScrapedShowtime] = []
    reported_count = 0

    for block in soup.select(_CINEMARK_MOVIE_BLOCK_SELECTOR):
        title_el = block.find("h3")
        raw_title = title_el.get_text(strip=True) if title_el else ""
        if not raw_title:
            continue
        base_title, is_70mm = _strip_cinemark_70mm_suffix(raw_title)

        times_container = block.select_one(".movieBlockShowtimes")
        if times_container is None:
            continue

        current_format: str | None = "70mm" if is_70mm else None
        for child in times_container.find_all(recursive=False):
            classes = child.get("class") or []
            if "attribute-list--auditorium-attributes" in classes:
                if is_70mm:
                    # The 70mm listing's own attribute-list text ("70mm")
                    # is redundant with the title-suffix signal already
                    # used to set current_format above; skipped so it
                    # can't be overridden by a different label later in
                    # the same listing.
                    continue
                current_format = _extract_cinemark_group_format(child)
            elif "showtimeMovieTimes" in classes:
                for showtime_div in child.select(".showtime"):
                    reported_count += 1
                    link = showtime_div.find("a")
                    href = (link.get("href") or "").strip() if link else ""
                    if not href:
                        continue
                    parsed = _parse_cinemark_ticket_url_showtime(href)
                    if parsed is None:
                        continue
                    showtimes.append(
                        ScrapedShowtime(
                            movie_title=base_title,
                            show_date=parsed.date(),
                            start_time=parsed.time(),
                            format=current_format or "Standard",
                            ticket_url=urljoin(base_url, href),
                        )
                    )

    return showtimes, reported_count


def _walk_cinemark_west_plano_dates(
    dates: list[date],
    fetch_date_fn: Callable[[date], str],
    base_url: str,
) -> ScrapeResult:
    """Fetch and parse one date's HTML per entry in `dates` (the site's
    own date-tab list, research.md §4), stopping early if a date's fetch
    raises after exhausting its own retries. Complete only when every
    date was fetched. Pure walking logic, independent of Playwright, so
    it can be unit tested with a fake `fetch_date_fn`."""
    showtimes: list[ScrapedShowtime] = []
    reported_count = 0
    complete = False
    incomplete_reason: str | None = None

    for show_date in dates:
        try:
            html = fetch_date_fn(show_date)
        except Exception as exc:  # noqa: BLE001 - any per-date failure ends the walk, not the run
            incomplete_reason = f"failed fetching {show_date.isoformat()}: {exc}"
            break
        day_showtimes, day_count = parse_cinemark_west_plano_html(html, base_url=base_url)
        showtimes.extend(day_showtimes)
        reported_count += day_count
    else:
        complete = True

    return ScrapeResult(
        showtimes=showtimes,
        reported_count=reported_count,
        complete=complete,
        incomplete_reason=incomplete_reason,
    )


def scrape_cinemark_west_plano_showtimes(
    source_url: str = "https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx",
    theater_id: str = CINEMARK_WEST_PLANO_THEATER_ID,
    timeout_ms: int = 30_000,
) -> ScrapeResult:
    """Fetch every showtime Cinemark West Plano currently has published,
    across every date its own date-tab strip currently offers
    (research.md §4), by calling the same Umbraco surface-controller
    endpoint the tab strip itself calls (research.md §1). One
    browser/context/page is reused across every date fetched in this
    run."""
    logger.info("Starting Cinemark West Plano showtime scrape for %s", source_url)
    split = urlsplit(source_url)
    origin = f"{split.scheme}://{split.netloc}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=REALISTIC_USER_AGENT)
            Stealth().apply_stealth_sync(context)
            page = context.new_page()

            index_html = _fetch_page_html_with_retry(page, source_url, timeout_ms)
            dates = extract_cinemark_west_plano_dates(index_html)

            def _fetch_date(show_date: date) -> str:
                url = (
                    f"{origin}/umbraco/surface/Showtimes/GetByTheaterId"
                    f"?theaterId={theater_id}&showDate={show_date.isoformat()}"
                )
                return _fetch_page_html_with_retry(page, url, timeout_ms)

            result = _walk_cinemark_west_plano_dates(dates, _fetch_date, base_url=origin)
        finally:
            browser.close()

    logger.info(
        "Cinemark West Plano scrape complete: %d showtime(s) parsed out of %d reported "
        "across %d date(s) (complete=%s)",
        len(result.showtimes), result.reported_count, len(dates), result.complete,
    )
    return result

