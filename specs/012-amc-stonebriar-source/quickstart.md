# Quickstart & Validation Guide: AMC Stonebriar 24 Showtime Ingestion

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This guide documents the procedures for executing and validating AMC Stonebriar 24 showtime
ingestion, following the same shape as the Angelika Dallas quickstart (spec 008).

## Prerequisites

- Python 3.11+ installed in local environment or virtual environment (`.venv`)
- Dependencies installed (`pip install -r requirements.txt`)
- Playwright browsers installed (`playwright install chromium`)

## Validation Scenarios

### Scenario 1: Run Ingestion against AMC Stonebriar 24

```bash
python -c "
from cinema_recs import storage
cinema = storage.ensure_amc_stonebriar_cinema('cinema.db')
print('Cinema ID:', cinema.id)
"

python -c "
from cinema_recs import storage, ingest
cinema = storage.get_cinema_by_name('cinema.db', 'AMC Stonebriar 24')
run = ingest.run_ingestion('cinema.db', cinema)
print('Ingestion Run Outcome:', run.outcome, '| Showtimes Captured:', run.showtimes_captured)
"
```

**Expected Outcome**:
- Ingestion run outcome is `"success"` (or `"partial"` if minor entries skipped).
- `showtimes_captured` > 0 when the site has scheduled showtimes.

---

### Scenario 2: Validate Ingested Showtimes and Presentation Formats

```bash
python -c "
from cinema_recs import storage
cinema = storage.get_cinema_by_name('cinema.db', 'AMC Stonebriar 24')
showtimes = storage.list_active_showtimes('cinema.db', cinema.id)
for s in showtimes[:10]:
    print(f'{s.show_date} {s.start_time} | {s.movie_title} | Format: {s.format} | URL: {s.ticket_url}')
"
```

**Expected Outcome**:
- Ingested records display valid dates, start times in Central Time, and (where applicable)
  presentation formats such as `LASER AT AMC`, `IMAX WITH LASER AT AMC`, `Dolby Cinema`, or
  `RealD 3D`.
- `ticket_url` values match `https://www.amctheatres.com/showtimes/<id>/seats`.

---

### Scenario 3: Verify Idempotency on Re-Run

```bash
python -c "
from cinema_recs import storage, ingest
cinema = storage.get_cinema_by_name('cinema.db', 'AMC Stonebriar 24')
run = ingest.run_ingestion('cinema.db', cinema)
showtimes = storage.list_active_showtimes('cinema.db', cinema.id)
print('Re-run outcome:', run.outcome, '| Total active showtimes:', len(showtimes))
"
```

**Expected Outcome**:
- No duplicate showtimes are created. Total active showtimes count remains equal to the unique
  set of currently-published sessions.

---

### Automated Unit & Integration Tests

```bash
pytest tests/unit/test_amc_stonebriar_scraper.py
pytest tests/integration/test_amc_stonebriar_ingestion.py
```
