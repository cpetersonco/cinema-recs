# Interface Contract: Texas Theatre Scraper

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md)

## Scrape Function Interface

### Function Signature
```python
def scrape_texas_theatre_showtimes(
    source_url: str = "https://thetexastheatre.com/calendar"
) -> ScraperResult
```

### Input Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source_url` | `str` | `"https://thetexastheatre.com/calendar"` | Target URL for fetching Texas Theatre calendar events |

### Return Value (`ScraperResult`)
```python
class ScrapedShowtime(NamedTuple):
    movie_title: str
    show_date: datetime.date
    start_time: datetime.time
    format: Optional[str]
    ticket_url: Optional[str]

class ScraperResult(NamedTuple):
    showtimes: list[ScrapedShowtime]
    reported_count: int
```

### Error Behaviors
- **Network / HTTP Error**: Raises `RuntimeError` or `PlaywrightError` with log message specifying failure detail. `run_ingestion` catches exception and records `outcome="failure"`.
- **Cloudflare / Bot Block**: Raises `RuntimeError("Blocked by Cloudflare")` when page HTML matches `BLOCK_PAGE_MARKERS`.
- **Parsing Errors**: Individual items missing required title or time fields are skipped; if items are skipped, `reported_count` > `len(showtimes)` and `run_ingestion` records `outcome="partial"`.
