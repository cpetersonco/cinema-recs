# Interface Contract: Cinemark West Plano Scraper

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

## Scrape Function Interface

### Function Signature
```python
def scrape_cinemark_west_plano_showtimes(
    source_url: str = "https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx",
    theater_id: str = "231",
) -> ScrapeResult
```

### Input Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_url` | `str` | West Plano theatre page URL | Fetched once to read the site's own date-tab strip (`a.showdate-link[data-datevalue]`, research.md §4) |
| `theater_id` | `str` | `"231"` | Cinemark's internal theater ID for West Plano, used as the `theaterId` query param on every `GetByTheaterId` call |

### Return Value (`ScrapeResult`)
```python
class ScrapedShowtime(NamedTuple):
    movie_title: str          # 70mm suffix stripped for 70mm listings (research.md §2)
    show_date: datetime.date
    start_time: datetime.time  # local wall-clock time, Central Time (research.md §5)
    format: str | None         # "Standard" | "70mm" | "XD" | "ScreenX" | "D-BOX" | "RealD 3D"
                                # | a "+"-joined compound (e.g. "XD+D-BOX") | None
    ticket_url: str | None     # resolved absolute TicketSeatMap URL

class ScrapeResult(NamedTuple):
    showtimes: list[ScrapedShowtime]
    reported_count: int
    complete: bool             # True only if every date in the date-tab list was fetched/parsed
    incomplete_reason: str | None
```

Identical shape to the Cinepolis, Texas Theatre, and Angelika Dallas scrape functions —
`ingest.py` and `storage.py` require no changes to consume this source's output.

### Error Behaviors
- **Network / Fetch Error on the initial theatre page (date-tab discovery)**: Raises the
  underlying Playwright/`RuntimeError` after exhausting `_fetch_page_html_with_retry`'s retries;
  `run_ingestion` catches it and records `outcome="failure"` with zero showtimes.
- **Network / Fetch Error on an individual date's `GetByTheaterId` call**: Logged and that date is
  skipped (matching Texas Theatre's per-page failure handling); the walk continues to the next
  date. `complete` is set to `False` and `incomplete_reason` records which date(s) failed.
  `run_ingestion` records `outcome="partial"` when `showtimes` is non-empty, or `"failure"` if
  every date failed.
- **Bot Block / Anti-Automation Response**: Raises `BlockedError` (existing exception class in
  `scraper.py`) if a response matches known block-page markers, consistent with the Cinepolis and
  Texas Theatre fetch paths.
- **Parsing Errors**: A showtime listing missing a required title, date, or time field is skipped;
  when any are skipped, `reported_count` > `len(showtimes)` and `run_ingestion` records
  `outcome="partial"`.
- **Ambiguous/Unrecognized Format Badge**: An `<img>` badge whose `alt` text doesn't match the
  known set (`Cinemark XD`, `D-BOX`, `ScreenX`, `RealD 3D`) is included verbatim in the joined
  format string rather than dropped, so novel Cinemark badges degrade gracefully instead of
  silently losing format information.

## Ingestion Dispatch Contract

`ingest.py`'s `run_ingestion()` dispatches via an explicit `Cinema.source_type -> scraper`
mapping (feature 011, commit `9718132` "Fix silent cinema-source misrouting" — domain-substring
dispatch was replaced project-wide precisely to stop a new/renamed source from silently falling
through to the wrong scraper). This feature adds one entry to that mapping:

```python
scrapers_by_source_type = {
    "cinepolis": scrape_showtimes,
    "texas_theatre": scrape_texas_theatre_showtimes,
    "angelika_dallas": scrape_angelika_dallas_showtimes,
    "cinemark_west_plano": scrape_cinemark_west_plano_showtimes,
}
```

`ensure_cinemark_west_plano_cinema()` MUST register the cinema with
`source_type="cinemark_west_plano"` (never inferred from `name`/`source_url`), so a future,
different Cinemark venue onboarded later gets its own distinct `source_type` rather than being
silently swallowed by a shared "cinemark" match.
