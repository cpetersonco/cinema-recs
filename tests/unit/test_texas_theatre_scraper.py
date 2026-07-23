from datetime import date, time

from cinema_recs.scraper import (
    extract_format,
    is_non_film_event,
    parse_texas_theatre_html,
)

# Fixtures below mirror the real thetexastheatre.com/calendar markup
# structure (verified against a live fetch during feature 006/007
# deployment debugging): one <title>Month Year | ...</title> for year
# context, and one <div class="calendar-listing"> per film with a
# `.tags span` classifying it (film / film_and_event / event-only), a
# title link, a single show date, and one <li> per showtime — each with
# its own ticket link and (usually) its own `.film-format` span.

SAMPLE_TEXAS_THEATRE_HTML = """
<!DOCTYPE html>
<html>
<head><title>July 2026 | The Texas Theatre</title></head>
<body>
<div id="calendar">
  <div class="calendar-listing">
    <div class="tags"><span class="film"></span></div>
    <h3><a href="/films-and-events/the-shining">THE SHINING</a></h3>
    <div class="listing-showtimes">
      <p>Showtimes: <span class="visually-hidden">Fri, Jul 25 </span></p>
      <ul class="times">
        <li>
          <a class="use-ajax" href="/order/add-tickets/1001/nojs">7:30pm</a>
          <span class="film-format">35mm</span>
        </li>
      </ul>
    </div>
  </div>
  <div class="calendar-listing">
    <div class="tags"><span class="film"></span></div>
    <h3><a href="/films-and-events/2001-a-space-odyssey">2001: A SPACE ODYSSEY</a></h3>
    <div class="listing-showtimes">
      <p>Showtimes: <span class="visually-hidden">Sat, Jul 26 </span></p>
      <ul class="times">
        <li>
          <a class="use-ajax" href="/order/add-tickets/1002/nojs">9:15pm</a>
          <span class="film-format">70mm</span>
        </li>
      </ul>
    </div>
  </div>
  <div class="calendar-listing">
    <div class="tags"><span class="film"></span></div>
    <h3><a href="/films-and-events/metropolis">METROPOLIS</a></h3>
    <div class="listing-showtimes">
      <p>Showtimes: <span class="visually-hidden">Sun, Jul 27 </span></p>
      <ul class="times">
        <li>
          <a href="" class="disabled">8:00pm</a>
        </li>
      </ul>
    </div>
  </div>
</div>
</body>
</html>
"""

SAMPLE_HTML_WITH_NON_FILM_EVENTS = """
<!DOCTYPE html>
<html>
<head><title>July 2026 | The Texas Theatre</title></head>
<body>
<div id="calendar">
  <div class="calendar-listing">
    <div class="tags"><span class="film"></span></div>
    <h3><a href="/films-and-events/the-shining">THE SHINING</a></h3>
    <div class="listing-showtimes">
      <p>Showtimes: <span class="visually-hidden">Fri, Jul 25 </span></p>
      <ul class="times">
        <li><a class="use-ajax" href="/order/add-tickets/1001/nojs">7:30pm</a></li>
      </ul>
    </div>
  </div>
  <div class="calendar-listing">
    <div class="tags"><span class="event"></span></div>
    <h3><a href="/films-and-events/comedy-night">Comedy Night Stand-Up Showcase</a></h3>
    <div class="listing-showtimes">
      <p>Showtimes: <span class="visually-hidden">Sat, Jul 26 </span></p>
      <ul class="times">
        <li><a class="use-ajax" href="/order/add-tickets/1003/nojs">9:00pm</a></li>
      </ul>
    </div>
  </div>
  <div class="calendar-listing">
    <div class="tags"><span class="film_and_event"></span></div>
    <h3><a href="/films-and-events/mv-showcase">Davis &amp; Pellington Music Video Showcase</a></h3>
    <div class="listing-showtimes">
      <p>Showtimes: <span class="visually-hidden">Sun, Jul 27 </span></p>
      <ul class="times">
        <li><a class="use-ajax" href="/order/add-tickets/1004/nojs">8:00pm</a></li>
      </ul>
    </div>
  </div>
</div>
</body>
</html>
"""

SAMPLE_MULTI_SHOWTIME_HTML = """
<!DOCTYPE html>
<html>
<head><title>July 2026 | The Texas Theatre</title></head>
<body>
<div id="calendar">
  <div class="calendar-listing">
    <div class="tags"><span class="film_and_event"></span></div>
    <h3><a href="/films-and-events/the-odyssey">The Odyssey</a></h3>
    <div class="special-note">
      <p><a href="/series-and-programs/screening-on-35mm">Screening on 35mm</a></p>
    </div>
    <div class="listing-showtimes">
      <p>Showtimes: <span class="visually-hidden">Wed, Jul 22 </span></p>
      <ul class="times">
        <li>
          <a class="use-ajax" href="/order/add-tickets/1975/nojs">5:45pm</a>
          <span class="film-format">35mm</span>
        </li>
        <li>
          <a class="use-ajax" href="/order/add-tickets/1976/nojs">9:10pm</a>
          <span class="film-format">35mm</span>
        </li>
      </ul>
    </div>
  </div>
</div>
</body>
</html>
"""


def test_extract_format_identifies_35mm_and_70mm():
    assert extract_format("THE SHINING - 35mm Print") == "35mm"
    assert extract_format("2001: A Space Odyssey [70mm]") == "70mm"
    assert extract_format("Special 16mm archival screening") == "16mm"
    assert extract_format("4K Restoration Edition") == "4K"
    assert extract_format("DCP Digital Presentation") == "Digital"
    assert extract_format("Standard digital presentation") == "Digital"
    assert extract_format("Regular movie title without format") is None


def test_parse_texas_theatre_html_extracts_showtimes():
    showtimes, count = parse_texas_theatre_html(SAMPLE_TEXAS_THEATRE_HTML)

    assert count == 3
    assert len(showtimes) == 3

    sh0 = showtimes[0]
    assert sh0.movie_title == "THE SHINING"
    assert sh0.show_date == date(2026, 7, 25)
    assert sh0.start_time == time(19, 30)
    assert sh0.format == "35mm"
    assert sh0.ticket_url == "https://thetexastheatre.com/order/add-tickets/1001/nojs"

    sh1 = showtimes[1]
    assert sh1.movie_title == "2001: A SPACE ODYSSEY"
    assert sh1.show_date == date(2026, 7, 26)
    assert sh1.start_time == time(21, 15)
    assert sh1.format == "70mm"

    # A "disabled" showtime (empty href, e.g. already past or sold out)
    # is still a real screening — captured with format/ticket_url absent
    # rather than fabricated, not dropped entirely.
    sh2 = showtimes[2]
    assert sh2.movie_title == "METROPOLIS"
    assert sh2.show_date == date(2026, 7, 27)
    assert sh2.start_time == time(20, 0)
    assert sh2.format is None
    assert sh2.ticket_url is None


def test_parse_texas_theatre_html_emits_one_showtime_per_li():
    showtimes, count = parse_texas_theatre_html(SAMPLE_MULTI_SHOWTIME_HTML)

    assert count == 2
    assert len(showtimes) == 2
    assert all(s.movie_title == "The Odyssey" for s in showtimes)
    assert all(s.show_date == date(2026, 7, 22) for s in showtimes)
    assert {s.start_time for s in showtimes} == {time(17, 45), time(21, 10)}
    assert all(s.format == "35mm" for s in showtimes)
    assert showtimes[0].ticket_url == "https://thetexastheatre.com/order/add-tickets/1975/nojs"
    assert showtimes[1].ticket_url == "https://thetexastheatre.com/order/add-tickets/1976/nojs"


def test_is_non_film_event_detects_comedy_and_music():
    assert is_non_film_event("Comedy Night Stand-Up Showcase") is True
    assert is_non_film_event("Live Music: Local Band Concert") is True
    assert is_non_film_event("Karaoke Night") is True
    assert is_non_film_event("THE SHINING (35mm Film Print)") is False
    assert is_non_film_event("") is False


def test_parse_texas_theatre_html_excludes_non_film_tagged_events():
    showtimes, count = parse_texas_theatre_html(SAMPLE_HTML_WITH_NON_FILM_EVENTS)

    assert count == 1
    assert len(showtimes) == 1
    assert showtimes[0].movie_title == "THE SHINING"
