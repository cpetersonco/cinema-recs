# Quickstart & Validation Guide: Texas Theatre Showtime Ingestion

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This guide documents the procedures for executing and validating Texas Theatre showtime ingestion.

## Prerequisites

- Python 3.11+ installed in local environment or virtual environment (`.venv`)
- Dependencies installed (`pip install -r requirements.txt`)
- Playwright browsers installed (`playwright install chromium`)

## Validation Scenarios

### Scenario 1: Run Ingestion against Texas Theatre Calendar

Execute the ingestion runner against the Texas Theatre cinema source:

```bash
# Register or ensure Texas Theatre cinema source exists in SQLite storage
python -c "
from cinema_recs import storage
cinema = storage.ensure_cinema('Texas Theatre', 'Oak Cliff, Dallas, TX', 'https://thetexastheatre.com/calendar', db_path='cinema.db')
print('Cinema ID:', cinema.id)
"

# Execute ingestion run
python -c "
from cinema_recs import storage, ingest
cinema = storage.get_cinema_by_name('Texas Theatre', db_path='cinema.db')
run = ingest.run_ingestion('cinema.db', cinema)
print('Ingestion Run Outcome:', run.outcome, '| Showtimes Captured:', run.showtimes_captured)
"
```

**Expected Outcome**:
- Ingestion run outcome is `"success"` (or `"partial"` if minor entries skipped).
- `showtimes_captured` > 0 when calendar has scheduled showtimes.

---

### Scenario 2: Validate Ingested Showtimes and Projection Formats

Query stored showtimes to verify movie titles, dates, times, format tags, and ticket links:

```bash
python -c "
from cinema_recs import storage
showtimes = storage.get_active_showtimes_for_cinema_name('Texas Theatre', db_path='cinema.db')
for s in showtimes[:10]:
    print(f'{s.show_date} {s.start_time} | {s.movie_title} | Format: {s.format} | URL: {s.ticket_url}')
"
```

**Expected Outcome**:
- Ingested records display valid dates, start times in Central Time, and extracted formats (e.g. `35mm`, `70mm`, `Digital`) where applicable.

---

### Scenario 3: Verify Idempotency on Re-Run

Execute a second ingestion run immediately following the first:

```bash
python -c "
from cinema_recs import storage, ingest
cinema = storage.get_cinema_by_name('Texas Theatre', db_path='cinema.db')
run = ingest.run_ingestion('cinema.db', cinema)
showtimes = storage.get_active_showtimes_for_cinema_name('Texas Theatre', db_path='cinema.db')
print('Re-run outcome:', run.outcome, '| Total active showtimes:', len(showtimes))
"
```

**Expected Outcome**:
- No duplicate showtimes are created. Total active showtimes count remains equal to unique calendar entries.

---

### Automated Unit & Integration Tests

Run unit tests for Texas Theatre calendar parsing:

```bash
pytest tests/unit/test_texas_theatre_scraper.py
```
