# Interface Contract: Angelika Film Center Dallas Scraper

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

## Scrape Function Interface

### Function Signature
```python
def scrape_angelika_dallas_showtimes(
    source_url: str = "https://angelikafilmcenter.com/dallas"
) -> ScrapeResult
```

### Input Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_url` | `str` | `"https://angelikafilmcenter.com/dallas"` | Angelika Dallas site URL (used to derive/confirm the Reading Cinemas `cinemaId`, not fetched as HTML directly — see research.md §1) |

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
```

Identical shape to the Cinepolis and Texas Theatre scrape functions — `ingest.py` and `storage.py`
require no changes to consume this source's output.

### Error Behaviors
- **Network / API Error**: Raises `RuntimeError` (or the underlying HTTP client's error) with a log
  message specifying failure detail. `run_ingestion` catches the exception and records
  `outcome="failure"`.
- **Bot Block / Anti-Automation Response**: Raises `BlockedError` (existing exception class in
  `scraper.py`) if the response matches known block-page markers, consistent with the Cinepolis and
  Texas Theatre fetch paths.
- **Parsing Errors**: Individual sessions missing a required title or time field are skipped; if any
  are skipped, `reported_count` > `len(showtimes)` and `run_ingestion` records `outcome="partial"`.
- **Non-Film Events**: Sessions identified as non-film (per research.md §5) are excluded from the
  returned `showtimes` list and are counted in `reported_count` but not treated as "skipped due to
  error" — this only affects `outcome` if the skip-count logic in `ingest.py` treats them the same
  as parse-skips (existing behavior, unchanged by this feature).

## Ingestion Dispatch Contract

`ingest.py`'s `run_ingestion()` MUST route calls to `scrape_angelika_dallas_showtimes()` when the
cinema's `source_url` contains `"angelikafilmcenter.com"`, following the existing domain-substring
dispatch pattern used for Texas Theatre:

```python
if "thetexastheatre.com" in cinema.source_url.lower() or "texas theatre" in cinema.name.lower():
    result = scrape_texas_theatre_showtimes(cinema.source_url)
elif "angelikafilmcenter.com" in cinema.source_url.lower() or "angelika" in cinema.name.lower():
    result = scrape_angelika_dallas_showtimes(cinema.source_url)
else:
    result = scrape_showtimes(cinema.source_url)
```

## Cinema Registration Contract

`storage.py` MUST expose an `ensure_angelika_dallas_cinema(db_path: str) -> Cinema` function
mirroring `ensure_texas_theatre_cinema`, using the `ANGELIKA_DALLAS_NAME` / `_LOCATION` / `_DEFAULT_URL`
constants defined in `config.py`. `main.py`'s `bootstrap()` MUST call it and append the result to the
`cinemas` list passed to `run_ingestion`, `run_notifications`, `start_scheduler`, and `create_app`.
