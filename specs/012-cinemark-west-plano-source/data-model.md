# Data Model: Cinemark West Plano XD and ScreenX Showtime Ingestion Source

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

## Existing entities used (unchanged)

This feature introduces no schema changes. It produces records in the shapes already defined in
`src/cinema_recs/models.py` and `src/cinema_recs/scraper.py`:

- **`Cinema`** (`models.py`): One new row, created via `ensure_cinemark_west_plano_cinema()`,
  with `source_type="cinemark_west_plano"`, `name="Cinemark West Plano XD and ScreenX"`,
  `location="Plano, TX"`, `source_url="https://www.cinemark.com/theatres/tx-plano/cinemark-west-plano-xd-and-screenx"`.
- **`Showtime`** (`models.py`): One row per ingested screening, keyed by the existing
  `(cinema_id, movie_title, show_date, start_time)` dedup tuple. `format` holds the value derived
  per research.md §2 (e.g. `"Standard"`, `"70mm"`, `"XD"`, `"ScreenX"`, `"D-BOX"`, `"RealD 3D"`,
  or a joined compound like `"XD+D-BOX"`). `ticket_url` holds the resolved `TicketSeatMap` URL.
- **`ScrapedShowtime`** (`scraper.py`, `NamedTuple`): `movie_title`, `show_date`, `start_time`,
  `format`, `ticket_url` — the in-memory shape `parse_cinemark_west_plano_html()` must produce.
  For a 70mm listing, `movie_title` is the base film title with the `" 70mm"` suffix stripped
  (e.g. `"The Odyssey"`, not `"The Odyssey 70mm"`), so it dedupes against the same film's
  non-70mm showtimes under one logical title.
- **`ScrapeResult`** (`scraper.py`, `NamedTuple`): `showtimes`, `reported_count`, `complete`,
  `incomplete_reason` — returned by `scrape_cinemark_west_plano_showtimes()`. `complete=True` only
  when every date in the site's own date-tab list (research.md §4) was successfully fetched and
  parsed; a mid-walk fetch failure after retries sets `complete=False` with `incomplete_reason`
  describing which date failed, matching the Texas Theatre per-page failure contract.
- **`IngestionRun`** (`models.py`): Recorded by the existing `run_ingestion()` orchestration —
  unchanged by this feature.

## New source-local concepts (not persisted as new tables — parsing-time only)

- **Format badge**: An `<img alt="...">` found in a showtime group's format-icon `<ul>`
  (`"Cinemark XD"`, `"D-BOX"`, `"ScreenX"`, `"RealD 3D"`). Normalized by stripping the `"Cinemark
  "` prefix where present (`"Cinemark XD"` → `"XD"`) before storing/joining.
- **70mm title suffix**: A case-insensitive `" 70mm"` suffix on a listing's movie title, detected
  and stripped during parsing to recover the base film title and set `format="70mm"` on that
  listing's showtimes (research.md §2).
- **Date-tab entry**: `data-datevalue="YYYY-MM-DD"` read from `a.showdate-link` elements on the
  main theatre page (research.md §4) — the driving input to the per-date `GetByTheaterId` fetch
  loop; not persisted, only used to construct fetch URLs during a scrape run.
