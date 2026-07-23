# Interface Contract: AMC Stonebriar 24 Scraper

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

## Scrape Function Interface

### Function Signature
```python
def scrape_amc_stonebriar_showtimes(
    source_url: str = "https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtimes",
    timeout_ms: int = 30_000,
) -> ScrapeResult
```

### Input Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_url` | `str` | AMC Stonebriar 24 showtimes URL (plural `/showtimes` — see research.md §1) | Page to load via Playwright |
| `timeout_ms` | `int` | `30_000` | Per-navigation/response timeout, matching Angelika Dallas's signature |

### Return Value (`ScrapeResult`)
```python
class ScrapedShowtime(NamedTuple):
    movie_title: str
    show_date: datetime.date
    start_time: datetime.time
    format: str | None
    ticket_url: str | None

class ScrapeResult(NamedTuple):
    showtimes: list[ScrapedShowtime]
    reported_count: int
    complete: bool = True
    incomplete_reason: str | None = None
```

Identical shape to every other source's scrape function — `ingest.py` and `storage.py` require no
changes to consume this source's output.

### Error Behaviors
- **Network / Navigation Error**: Raises `RuntimeError`/`PlaywrightError`/`PlaywrightTimeoutError`
  with a log message specifying failure detail. `run_ingestion` catches the exception and records
  `outcome="failure"`.
- **Bot Block / Anti-Automation Response**: Raises `BlockedError` (existing exception class in
  `scraper.py`) when the response matches known block-page markers (`BLOCK_PAGE_MARKERS`) or when
  the Playwright browser context is redirected to the `queue.amctheatres.com` gate observed in
  research.md §2 — the marker list MUST be extended to detect this source's specific gate/redirect
  pattern, not just the existing Cloudflare challenge-page text.
- **Parsing Errors**: Individual showtimes missing a required title or time field are skipped; if
  any are skipped, `reported_count` > `len(showtimes)` and `run_ingestion` records
  `outcome="partial"`.
- **Multi-day walk incompletion**: If the fetch stops before reaching the source's own end of its
  published date range (per-day fetch failure after retries), `complete=False` and
  `incomplete_reason` is set, matching the Texas Theatre/Angelika Dallas walk contract — `ingest.py`
  already skips stale-marking in this case unchanged.

## Ingestion Dispatch Contract

`ingest.py`'s `run_ingestion()` dispatches via the explicit `source_type` -> scraper mapping
(feature 011 spec FR-001; no substring matching):

```python
scrapers_by_source_type = {
    "cinepolis": scrape_showtimes,
    "texas_theatre": scrape_texas_theatre_showtimes,
    "angelika_dallas": scrape_angelika_dallas_showtimes,
    "amc_stonebriar": scrape_amc_stonebriar_showtimes,
}
```

## Cinema Registration Contract

`storage.py` MUST expose an `ensure_amc_stonebriar_cinema(db_path: str) -> Cinema` function
mirroring `ensure_angelika_dallas_cinema`, using `AMC_STONEBRIAR_NAME` / `_LOCATION` /
`_DEFAULT_URL` constants defined in `config.py`, and registering the cinema with
`source_type="amc_stonebriar"`. `main.py`'s `bootstrap()` MUST call it and append the result to the
`cinemas` list passed to `run_ingestion`, `run_notifications`, `start_scheduler`, and `create_app`.
