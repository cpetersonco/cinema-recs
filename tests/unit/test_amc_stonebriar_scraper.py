from datetime import date, time

from cinema_recs.scraper import (
    _amc_stonebriar_looks_like_queue_gate,
    _extract_amc_stonebriar_dates,
    _parse_amc_stonebriar_time,
    _walk_amc_stonebriar_dates,
    parse_amc_stonebriar_html,
)

# Fixtures below mirror the real amctheatres.com showtimes page structure
# (verified against a live fetch of
# https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtimes
# during feature 012 planning/implementation, see research.md §3 and tasks.md
# T003): one <section> per film with an <h1> title, and one
# <li aria-label="{Format Name} Showtimes"> per presentation format, each
# containing <a href="https://www.amctheatres.com/showtimes/{id}"> anchors
# whose own text carries the display time (plus, sometimes, trailing badge
# text like "ALMOST FULL" or "20% OFF" in the same link).

SAMPLE_AMC_STONEBRIAR_HTML = """
<!DOCTYPE html>
<html>
<body>
<main>
  <section>
    <header><h1>Moana</h1><h2>AMC Stonebriar 24</h2></header>
    <ul class="flex flex-col gap-14 py-4 pl-1">
      <li aria-label="RealD 3D Showtimes">
        <h3><span>RealD 3D</span><span>: </span><span>PREMIUM 3D EXPERIENCE</span></h3>
        <ul class="flex flex-wrap">
          <li><a href="https://www.amctheatres.com/showtimes/145327760">12:15pm UP TO 15% OFF</a></li>
        </ul>
      </li>
      <li aria-label="Laser at AMC Showtimes">
        <h3><span>Laser at AMC</span><span>: </span><span>PICTURE A BETTER WORLD</span></h3>
        <ul class="flex flex-wrap">
          <li><a href="https://www.amctheatres.com/showtimes/145327763">6:15pm</a></li>
          <li><a href="https://www.amctheatres.com/showtimes/145327762">9:15pm</a></li>
        </ul>
      </li>
    </ul>
  </section>
  <section>
    <header><h1>The Odyssey</h1><h2>AMC Stonebriar 24</h2></header>
    <ul class="flex flex-col gap-14 py-4 pl-1">
      <li aria-label="IMAX with Laser at AMC Showtimes">
        <h3><span>IMAX with Laser at AMC</span><span>: </span><span>EXTRAORDINARY AWAITS</span></h3>
        <ul class="flex flex-wrap">
          <li><a href="https://www.amctheatres.com/showtimes/143799404">6:00pm ALMOST FULL</a></li>
          <li><a href="https://www.amctheatres.com/showtimes/143799405">10:00pm ALMOST FULL</a></li>
        </ul>
      </li>
    </ul>
  </section>
  <section>
    <header><h1>Private Theatre Rental</h1><h2>AMC Stonebriar 24</h2></header>
    <ul class="flex flex-col gap-14 py-4 pl-1">
      <li aria-label="Private Theatre Rentals Showtimes">
        <h3><span>Private Theatre Rentals</span><span>: </span><span>AT AMC</span></h3>
        <ul class="flex flex-wrap">
          <li><a href="https://www.amctheatres.com/showtimes/199999999">7:00pm</a></li>
        </ul>
      </li>
    </ul>
  </section>
</main>
</body>
</html>
"""

SAMPLE_AMC_STONEBRIAR_HTML_WITH_DATE_SELECT = """
<!DOCTYPE html>
<html>
<body>
<select name="date">
  <option value="">Today</option>
  <option value="2026-07-24">Fri, Jul 24</option>
  <option value="2026-07-25">Sat, Jul 25</option>
</select>
</body>
</html>
"""


def test_parse_amc_stonebriar_time_ignores_trailing_badge_text():
    assert _parse_amc_stonebriar_time("6:15pm") == time(18, 15)
    assert _parse_amc_stonebriar_time("6:00pm ALMOST FULL") == time(18, 0)
    assert _parse_amc_stonebriar_time("12:15pm UP TO 15% OFF") == time(12, 15)
    assert _parse_amc_stonebriar_time("not a time") is None


def test_parse_amc_stonebriar_html_extracts_showtimes_and_formats():
    showtimes, count = parse_amc_stonebriar_html(SAMPLE_AMC_STONEBRIAR_HTML, date(2026, 7, 23))

    # 5 real showtimes reported (1 RealD 3D + 2 Laser + 2 IMAX); the
    # Private Theatre Rental listing is excluded before being counted.
    assert count == 5
    assert len(showtimes) == 5
    assert all(s.show_date == date(2026, 7, 23) for s in showtimes)

    moana_times = {s.start_time: s.format for s in showtimes if s.movie_title == "Moana"}
    assert moana_times == {
        time(12, 15): "RealD 3D",
        time(18, 15): "Laser at AMC",
        time(21, 15): "Laser at AMC",
    }

    odyssey = [s for s in showtimes if s.movie_title == "The Odyssey"]
    assert len(odyssey) == 2
    assert all(s.format == "IMAX with Laser at AMC" for s in odyssey)
    assert {s.start_time for s in odyssey} == {time(18, 0), time(22, 0)}

    assert not any(s.movie_title == "Private Theatre Rental" for s in showtimes)


def test_parse_amc_stonebriar_html_builds_seats_ticket_url():
    showtimes, _ = parse_amc_stonebriar_html(SAMPLE_AMC_STONEBRIAR_HTML, date(2026, 7, 23))
    sh = next(s for s in showtimes if s.start_time == time(18, 15))
    assert sh.ticket_url == "https://www.amctheatres.com/showtimes/145327763/seats"


def test_amc_stonebriar_looks_like_queue_gate():
    assert _amc_stonebriar_looks_like_queue_gate(
        "https://queue.amctheatres.com/?c=amctheatres&e=globalsafetynetweb"
    ) is True
    assert _amc_stonebriar_looks_like_queue_gate(
        "https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtimes"
    ) is False


# --- Full showtime window (research.md §5): native <select name="date"> walk ---

BASE_URL = "https://www.amctheatres.com/movie-theatres/dallas-ft-worth/amc-stonebriar-24/showtimes"


def test_extract_amc_stonebriar_dates_reads_select_options():
    dates = _extract_amc_stonebriar_dates(
        SAMPLE_AMC_STONEBRIAR_HTML_WITH_DATE_SELECT, today=date(2026, 7, 23)
    )
    assert dates == [date(2026, 7, 23), date(2026, 7, 24), date(2026, 7, 25)]


def test_extract_amc_stonebriar_dates_falls_back_to_today_when_select_absent():
    dates = _extract_amc_stonebriar_dates("<html><body>no select here</body></html>", today=date(2026, 7, 23))
    assert dates == [date(2026, 7, 23)]


def test_walk_amc_stonebriar_dates_fetches_one_page_per_date():
    dates = [date(2026, 7, 23), date(2026, 7, 24)]
    pages = {
        BASE_URL: SAMPLE_AMC_STONEBRIAR_HTML,
        f"{BASE_URL}?date=2026-07-24": "<html><body></body></html>",
    }
    fetched = []

    def fetch_page_fn(url):
        fetched.append(url)
        return pages[url]

    result = _walk_amc_stonebriar_dates(fetch_page_fn, BASE_URL, dates)

    assert fetched == [BASE_URL, f"{BASE_URL}?date=2026-07-24"]
    assert len(result.showtimes) == 5
    assert result.complete is True
    assert result.incomplete_reason is None


def test_walk_amc_stonebriar_dates_marks_incomplete_when_a_day_fails():
    dates = [date(2026, 7, 23), date(2026, 7, 24), date(2026, 7, 25)]
    pages = {BASE_URL: SAMPLE_AMC_STONEBRIAR_HTML}

    def fetch_page_fn(url):
        if url not in pages:
            raise RuntimeError("Blocked by bot protection")
        return pages[url]

    result = _walk_amc_stonebriar_dates(fetch_page_fn, BASE_URL, dates)

    assert len(result.showtimes) == 5
    assert result.complete is False
    assert "2026-07-24" in result.incomplete_reason
