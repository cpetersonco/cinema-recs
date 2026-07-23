from datetime import date, time

from cinema_recs.scraper import (
    extract_format,
    is_non_film_event,
    parse_texas_theatre_html,
)

SAMPLE_HTML_WITH_NON_FILM_EVENTS = """
<!DOCTYPE html>
<html>
<body>
<div class="calendar-events">
  <article class="event-item">
    <h2 class="event-title"><a href="https://thetexastheatre.com/event/the-shining-35mm/">THE SHINING (35mm Film Print)</a></h2>
    <div class="event-date">July 25, 2026</div>
    <div class="event-time">7:30 PM</div>
  </article>
  <article class="event-item">
    <h3 class="event-title">Comedy Night Stand-Up Showcase</h3>
    <div class="event-date">July 26, 2026</div>
    <div class="event-time">9:00 PM</div>
  </article>
  <article class="event-item">
    <h3 class="event-title">Live Music: Local Band Concert</h3>
    <div class="event-date">July 27, 2026</div>
    <div class="event-time">8:00 PM</div>
  </article>
</div>
</body>
</html>
"""

SAMPLE_TEXAS_THEATRE_HTML = """
<!DOCTYPE html>
<html>
<body>
<div class="calendar-events">
  <article class="event-item">
    <h2 class="event-title"><a href="https://thetexastheatre.com/event/the-shining-35mm/">THE SHINING (35mm Film Print)</a></h2>
    <div class="event-date">July 25, 2026</div>
    <div class="event-time">7:30 PM</div>
  </article>
  <article class="event-item">
    <h3 class="event-title"><a href="/event/2001-a-space-odyssey-70mm/">2001: A SPACE ODYSSEY [70mm]</a></h3>
    <div class="event-details">Date: 2026-07-26 at 9:15 pm</div>
  </article>
  <article class="event-item">
    <h4 class="event-title">METROPOLIS (Silent Film w/ Live Organ)</h4>
    <div class="event-date">July 27, 2026</div>
    <div class="event-time">8:00 PM</div>
  </article>
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

    # Check 35mm event
    sh0 = showtimes[0]
    assert "THE SHINING" in sh0.movie_title
    assert sh0.show_date == date(2026, 7, 25)
    assert sh0.start_time == time(19, 30)
    assert sh0.format == "35mm"
    assert sh0.ticket_url == "https://thetexastheatre.com/event/the-shining-35mm/"

    # Check 70mm event
    sh1 = showtimes[1]
    assert "2001: A SPACE ODYSSEY" in sh1.movie_title
    assert sh1.show_date == date(2026, 7, 26)
    assert sh1.start_time == time(21, 15)
    assert sh1.format == "70mm"
    assert sh1.ticket_url == "https://thetexastheatre.com/event/2001-a-space-odyssey-70mm/"

    # Check event without format
    sh2 = showtimes[2]
    assert "METROPOLIS" in sh2.movie_title
    assert sh2.show_date == date(2026, 7, 27)
    assert sh2.start_time == time(20, 0)
    assert sh2.format is None


def test_is_non_film_event_detects_comedy_and_music():
    assert is_non_film_event("Comedy Night Stand-Up Showcase") is True
    assert is_non_film_event("Live Music: Local Band Concert") is True
    assert is_non_film_event("Karaoke Night") is True
    assert is_non_film_event("THE SHINING (35mm Film Print)") is False
    assert is_non_film_event("") is False


def test_parse_texas_theatre_html_excludes_non_film_events():
    showtimes, count = parse_texas_theatre_html(SAMPLE_HTML_WITH_NON_FILM_EVENTS)

    assert count == 1
    assert len(showtimes) == 1
    assert "THE SHINING" in showtimes[0].movie_title
