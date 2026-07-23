from datetime import date, time

from cinema_recs.scraper import (
    _walk_cinemark_west_plano_dates,
    extract_cinemark_west_plano_dates,
    parse_cinemark_west_plano_html,
)

# Fixture markup mirrors the real GET /umbraco/surface/Showtimes/GetByTheaterId
# response for Cinemark West Plano (theaterId=231), confirmed via live network
# inspection during feature 012 planning (see research.md §1/§2): one
# div[class*="showtimeMovieBlock"] per film, each holding a
# ".movieBlockShowtimes" whose direct children are a flat, repeating sequence
# of "ul.attribute-list--auditorium-attributes" (format group marker) followed
# by one or more "div.showtimeMovieTimes" blocks.

SAMPLE_DATE_TAB_HTML = """
<div id="showtimes-date-tabs">
  <a class="showdate-link" data-datevalue="2026-07-24">Today</a>
  <a class="showdate-link" data-datevalue="2026-07-24">Today</a>
  <a class="showdate-link" data-datevalue="2026-07-25">Fri 7/25</a>
  <a class="showdate-link" data-datevalue="2026-07-26">Sat 7/26</a>
</div>
"""

SAMPLE_SHOWTIMES_HTML = """
<div class="showtimeMovieBlock 108919">
  <h3 id="108919">The Odyssey</h3>
  <div class="movieBlockShowtimes">
    <ul class="attribute-list attribute-list--auditorium-attributes">
      <li class="attribute-list__item attribute-list__item--image">
        <a class="showtime-attribute-item"><img class="cinemarkxd" alt="Cinemark XD"></a>
      </li>
      <li class="attribute-list__item attribute-list__item--image">
        <a class="showtime-attribute-item"><img class="d-box" alt="D-BOX"></a>
      </li>
    </ul>
    <ul class="attribute-list attribute-list--showtime-attributes">
      <li class="attribute-list__item">Luxury Lounger</li>
    </ul>
    <div class="showtimeMovieTimes clearfix">
      <div class="row">
        <div class="showtime">
          <a class="showtime-link"
             href="/TicketSeatMap/?ShowtimeId=865297&amp;Showtime=2026-07-24T08:00:00">8:00am</a>
        </div>
      </div>
    </div>
    <ul class="attribute-list attribute-list--auditorium-attributes">
      <li class="attribute-list__item attribute-list__item--image">
        <a class="showtime-attribute-item"><img class="d-box" alt="D-BOX"></a>
      </li>
      <li class="attribute-list__item attribute-list__item--text">Standard Format</li>
    </ul>
    <ul class="attribute-list attribute-list--showtime-attributes"></ul>
    <div class="showtimeMovieTimes clearfix">
      <div class="row">
        <div class="showtime">
          <a class="showtime-link"
             href="/TicketSeatMap/?ShowtimeId=865310&amp;Showtime=2026-07-24T08:30:00">8:30am</a>
        </div>
      </div>
    </div>
    <div class="showtimeMovieTimes showtimeMovieTimes--lateNight clearfix">
      <div class="row">
        <div class="showtime">
          <a class="showtime-link"
             href="/TicketSeatMap/?ShowtimeId=865312&amp;Showtime=2026-07-25T00:01:00">12:01am</a>
        </div>
      </div>
    </div>
    <ul class="attribute-list attribute-list--auditorium-attributes">
      <li class="attribute-list__item attribute-list__item--text">Standard Format</li>
    </ul>
    <div class="showtimeMovieTimes clearfix">
      <div class="row">
        <div class="showtime">
          <a class="showtime-link"
             href="/TicketSeatMap/?ShowtimeId=871688&amp;Showtime=2026-07-24T09:05:00">9:05am</a>
        </div>
        <div class="showtime">
          <a href="">Sold Out</a>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="showtimeMovieBlock 110535">
  <h3 id="110535">The Odyssey 70mm</h3>
  <div class="movieBlockShowtimes">
    <ul class="attribute-list attribute-list--auditorium-attributes">
      <li class="attribute-list__item attribute-list__item--text">70mm</li>
    </ul>
    <div class="showtimeMovieTimes clearfix">
      <div class="row">
        <div class="showtime">
          <a class="showtime-link"
             href="/TicketSeatMap/?ShowtimeId=865306&amp;Showtime=2026-07-24T10:50:00">10:50am</a>
        </div>
      </div>
    </div>
  </div>
</div>
<div class="showtimeMovieBlock 222222">
  <h3 id="222222">No Format Info Film</h3>
  <div class="movieBlockShowtimes">
    <div class="showtimeMovieTimes clearfix">
      <div class="row">
        <div class="showtime">
          <a class="showtime-link"
             href="/TicketSeatMap/?ShowtimeId=700001&amp;Showtime=2026-07-24T19:00:00">7:00pm</a>
        </div>
      </div>
    </div>
  </div>
</div>
"""


def test_extract_cinemark_west_plano_dates_dedupes_and_preserves_order():
    dates = extract_cinemark_west_plano_dates(SAMPLE_DATE_TAB_HTML)
    assert dates == [date(2026, 7, 24), date(2026, 7, 25), date(2026, 7, 26)]


def test_parse_cinemark_west_plano_html_extracts_base_showtime_fields():
    showtimes, reported_count = parse_cinemark_west_plano_html(SAMPLE_SHOWTIMES_HTML)

    xd_dbox = next(s for s in showtimes if s.start_time == time(8, 0))
    assert xd_dbox.movie_title == "The Odyssey"
    assert xd_dbox.show_date == date(2026, 7, 24)
    assert xd_dbox.ticket_url == (
        "https://www.cinemark.com/TicketSeatMap/?ShowtimeId=865297&Showtime=2026-07-24T08:00:00"
    )
    # Sold-out/href-less showtime is counted but not returned as a real
    # showtime record.
    assert reported_count == len(showtimes) + 1


def test_parse_cinemark_west_plano_html_multi_badge_format_joined():
    showtimes, _ = parse_cinemark_west_plano_html(SAMPLE_SHOWTIMES_HTML)
    xd_dbox = next(s for s in showtimes if s.start_time == time(8, 0))
    assert xd_dbox.format == "XD+D-BOX"


def test_parse_cinemark_west_plano_html_badge_with_standard_text_tagged_by_badge():
    showtimes, _ = parse_cinemark_west_plano_html(SAMPLE_SHOWTIMES_HTML)
    dbox_only = next(s for s in showtimes if s.start_time == time(8, 30))
    assert dbox_only.format == "D-BOX"


def test_parse_cinemark_west_plano_html_late_night_block_inherits_preceding_format():
    showtimes, _ = parse_cinemark_west_plano_html(SAMPLE_SHOWTIMES_HTML)
    late_night = next(s for s in showtimes if s.start_time == time(0, 1))
    assert late_night.show_date == date(2026, 7, 25)
    assert late_night.format == "D-BOX"


def test_parse_cinemark_west_plano_html_text_only_group_normalizes_to_standard():
    showtimes, _ = parse_cinemark_west_plano_html(SAMPLE_SHOWTIMES_HTML)
    standard_only = next(s for s in showtimes if s.start_time == time(9, 5))
    assert standard_only.format == "Standard"


def test_parse_cinemark_west_plano_html_strips_70mm_title_suffix_and_tags_format():
    showtimes, _ = parse_cinemark_west_plano_html(SAMPLE_SHOWTIMES_HTML)
    seventymm = next(s for s in showtimes if s.start_time == time(10, 50))
    assert seventymm.movie_title == "The Odyssey"
    assert seventymm.format == "70mm"


def test_parse_cinemark_west_plano_html_missing_format_group_defaults_to_standard():
    showtimes, _ = parse_cinemark_west_plano_html(SAMPLE_SHOWTIMES_HTML)
    no_format_info = next(s for s in showtimes if s.start_time == time(19, 0))
    assert no_format_info.format == "Standard"


def test_parse_cinemark_west_plano_html_no_listings_returns_empty():
    showtimes, reported_count = parse_cinemark_west_plano_html("<div></div>")
    assert showtimes == []
    assert reported_count == 0


def test_walk_cinemark_west_plano_dates_complete_when_all_dates_fetch():
    dates = [date(2026, 7, 24), date(2026, 7, 25)]
    calls = []

    def fetch(show_date):
        calls.append(show_date)
        return SAMPLE_SHOWTIMES_HTML

    result = _walk_cinemark_west_plano_dates(
        dates, fetch, base_url="https://www.cinemark.com"
    )

    single_date_showtimes, single_date_reported_count = parse_cinemark_west_plano_html(
        SAMPLE_SHOWTIMES_HTML
    )

    assert calls == dates
    assert result.complete is True
    assert result.incomplete_reason is None
    assert len(result.showtimes) == len(dates) * len(single_date_showtimes)
    assert result.reported_count == len(dates) * single_date_reported_count


def test_walk_cinemark_west_plano_dates_incomplete_on_fetch_failure():
    dates = [date(2026, 7, 24), date(2026, 7, 25), date(2026, 7, 26)]

    def fetch(show_date):
        if show_date == date(2026, 7, 25):
            raise RuntimeError("boom")
        return SAMPLE_SHOWTIMES_HTML

    result = _walk_cinemark_west_plano_dates(
        dates, fetch, base_url="https://www.cinemark.com"
    )

    assert result.complete is False
    assert "2026-07-25" in result.incomplete_reason
    # Only the first date's showtimes were captured before the walk stopped.
    assert result.reported_count > 0
