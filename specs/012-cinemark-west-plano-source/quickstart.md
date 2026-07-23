# Quickstart & Validation Guide: Cinemark West Plano Showtime Ingestion

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This guide documents the procedures for executing and validating Cinemark West Plano showtime
ingestion, following the same shape as the Texas Theatre (006) and Angelika Dallas (008)
quickstarts.

## Prerequisites

- Python 3.11+ installed in local environment or virtual environment (`.venv`)
- Dependencies installed (`pip install -r requirements.txt`)
- Playwright browsers installed (`playwright install chromium`)

## Validation Scenarios

### Scenario 1: Run Ingestion against Cinemark West Plano

```bash
python -c "
from cinema_recs import storage
cinema = storage.ensure_cinemark_west_plano_cinema('cinema.db')
print('Cinema ID:', cinema.id)
"

python -c "
from cinema_recs import storage, ingest
cinema = storage.get_cinema_by_name('cinema.db', 'Cinemark West Plano XD and ScreenX')
run = ingest.run_ingestion('cinema.db', cinema)
print('Ingestion Run Outcome:', run.outcome, '| Showtimes Captured:', run.showtimes_captured)
"
```

**Expected Outcome**:
- Ingestion run outcome is `"success"` (or `"partial"` if minor entries/dates were skipped).
- `showtimes_captured` > 0 — expect a large count given ~75 published dates across dozens of films.

---

### Scenario 2: Validate 70mm and Special-Format Tagging (US2 / FR-003 / FR-004)

```bash
python -c "
from cinema_recs import storage
cinema = storage.get_cinema_by_name('cinema.db', 'Cinemark West Plano XD and ScreenX')
showtimes = storage.list_active_showtimes('cinema.db', cinema.id)
seventymm = [s for s in showtimes if s.format == '70mm']
for s in seventymm[:5]:
    print(f'{s.show_date} {s.start_time} | {s.movie_title} | Format: {s.format} | URL: {s.ticket_url}')
formats = sorted({s.format for s in showtimes if s.format})
print('Distinct formats seen:', formats)
"
```

**Expected Outcome**:
- At least one showtime has `format == \"70mm\"` while ingesting a period where "The Odyssey 70mm"
  (or another current 70mm listing) is scheduled, and its `movie_title` is the base film title
  (e.g. `"The Odyssey"`), not `"The Odyssey 70mm"`.
- `formats` includes distinct values for `Standard`, `70mm`, and at least one of `XD`, `ScreenX`,
  `D-BOX`, `RealD 3D` (or a joined compound like `XD+D-BOX`) — never a generic catch-all like
  `"Special"`.

---

### Scenario 3: Verify Idempotency on Re-Run

```bash
python -c "
from cinema_recs import storage, ingest
cinema = storage.get_cinema_by_name('cinema.db', 'Cinemark West Plano XD and ScreenX')
run = ingest.run_ingestion('cinema.db', cinema)
showtimes = storage.list_active_showtimes('cinema.db', cinema.id)
print('Re-run outcome:', run.outcome, '| Total active showtimes:', len(showtimes))
"
```

**Expected Outcome**:
- No duplicate showtimes are created. Total active showtimes count remains equal to the unique
  set of currently-published sessions across all walked dates.

---

### Automated Unit & Integration Tests

```bash
pytest tests/unit/test_cinemark_west_plano_scraper.py
pytest tests/integration/test_cinemark_west_plano_ingestion.py
```

Unit tests should specifically cover (research.md §2):
- A movie title ending in `" 70mm"` is stripped to its base title and tagged `format="70mm"`.
- A showtime group carrying two format badges (e.g. XD + D-BOX) produces a single joined format
  value rather than only the first badge.
- A showtime group with no badge and no `"Standard Format"` text still resolves to a sane default
  (`"Standard"` or `None`, per implementation) rather than raising.
