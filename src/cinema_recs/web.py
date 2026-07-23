import os

from flask import Flask, render_template_string

from cinema_recs.config import Config
from cinema_recs.models import Cinema, Showtime
from cinema_recs.storage import (
    get_latest_ingestion_run,
    get_letterboxd_movie_data,
    get_movie_metadata,
    get_movie_recommendation,
    list_active_showtimes,
)

LETTERBOXD_FILM_BASE_URL = "https://letterboxd.com/film"

TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w200"

LISTING_TEMPLATE = """
<!doctype html>
<title>Showtimes</title>
{% for section in cinema_sections %}
<h1>{{ section.cinema.name }} Showtimes</h1>
{% if section.showtimes %}
<table border="1" cellpadding="6">
  <tr><th>Movie</th><th>Date</th><th>Start Time</th><th>Format</th><th>Tickets</th>
      <th>Genre</th><th>Rating</th><th>Poster</th><th>Recommended</th></tr>
  {% for s in section.showtimes %}
  {% set recommendation = section.recommendations.get(s.movie_title) %}
  <tr{% if recommendation and recommendation.is_recommended %} style="background-color: #fff3cd;"{% endif %}>
    <td>{{ s.movie_title }}</td>
    <td>{{ s.show_date }}</td>
    <td>{{ s.start_time }}</td>
    <td>{{ s.format or "—" }}</td>
    <td>
      {% if s.ticket_url %}
      <a href="{{ s.ticket_url }}">Buy tickets</a>
      {% else %}
      —
      {% endif %}
    </td>
    {% set metadata = section.metadata.get(s.movie_title) %}
    {% if metadata and metadata.match_status == "matched" %}
    <td>{{ metadata.genres or "—" }}</td>
    {% else %}
    <td>—</td>
    {% endif %}
    {% set lb = section.letterboxd.get(s.movie_title) %}
    <td>
      {% if lb and lb.letterboxd_slug and lb.average_rating is not none %}
      <a href="{{ letterboxd_base_url }}/{{ lb.letterboxd_slug }}/">{{ lb.average_rating }}</a>
      {% elif metadata and metadata.average_rating is not none %}
      {{ metadata.average_rating }}
      {% else %}
      —
      {% endif %}
    </td>
    {% if metadata and metadata.match_status == "matched" %}
    <td>
      {% if metadata.poster_path %}
      <img src="{{ poster_base_url }}{{ metadata.poster_path }}" alt="{{ s.movie_title }} poster" height="60">
      {% else %}
      —
      {% endif %}
    </td>
    {% else %}
    <td>—</td>
    {% endif %}
    <td>
      {% if recommendation and recommendation.is_recommended %}
      ⭐ Recommended ({{ recommendation.reasons }})
      {% else %}
      —
      {% endif %}
    </td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p>No showtimes ingested yet.</p>
{% endif %}
{% endfor %}
<p><a href="/health">Ingestion health</a></p>
"""

HEALTH_TEMPLATE = """
<!doctype html>
<title>Ingestion Health</title>
<p>Running version: <strong>{{ app_version }}</strong></p>
{% for section in cinema_runs %}
<h1>{{ section.cinema.name }} Ingestion Health</h1>
{% set run = section.run %}
{% if run %}
<p>Outcome: <strong>{{ run.outcome|upper }}</strong></p>
<p>Started: {{ run.started_at }}</p>
<p>Finished: {{ run.finished_at }}</p>
<p>Showtimes captured: {{ run.showtimes_captured }}</p>
{% if run.error_message %}
<p>Error: {{ run.error_message }}</p>
{% endif %}
{% else %}
<p>No ingestion runs have completed yet.</p>
{% endif %}
{% endfor %}
<p><a href="/">Back to listing</a></p>
"""


def _group_by_earliest_showtime_per_movie(showtimes: list[Showtime]) -> list[Showtime]:
    """One Showtime per distinct movie_title, keeping the first occurrence.

    `list_active_showtimes` already orders results by `show_date,
    start_time`, so the first showtime seen per movie is that movie's
    earliest upcoming one — the same "earliest active showtime" concept
    `storage.get_next_showtime_for_movie` already uses elsewhere (feature
    010 spec FR-002), derived here with no extra query."""
    earliest_by_title: dict[str, Showtime] = {}
    for showtime in showtimes:
        earliest_by_title.setdefault(showtime.movie_title, showtime)
    return list(earliest_by_title.values())


def create_app(config: Config, cinemas: list[Cinema]) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def listing():
        cinema_sections = []
        for cinema in cinemas:
            showtimes = _group_by_earliest_showtime_per_movie(
                list_active_showtimes(config.db_path, cinema.id)
            )
            distinct_titles = {s.movie_title for s in showtimes}
            cinema_sections.append(
                {
                    "cinema": cinema,
                    "showtimes": showtimes,
                    "metadata": {
                        title: get_movie_metadata(config.db_path, title)
                        for title in distinct_titles
                    },
                    "recommendations": {
                        title: get_movie_recommendation(config.db_path, title)
                        for title in distinct_titles
                    },
                    "letterboxd": {
                        title: get_letterboxd_movie_data(config.db_path, title)
                        for title in distinct_titles
                    },
                }
            )
        return render_template_string(
            LISTING_TEMPLATE,
            cinema_sections=cinema_sections,
            poster_base_url=TMDB_POSTER_BASE_URL,
            letterboxd_base_url=LETTERBOXD_FILM_BASE_URL,
        )

    @app.get("/health")
    def health():
        cinema_runs = [
            {"cinema": cinema, "run": get_latest_ingestion_run(config.db_path, cinema.id)}
            for cinema in cinemas
        ]
        return render_template_string(
            HEALTH_TEMPLATE,
            cinema_runs=cinema_runs,
            app_version=os.environ.get("APP_VERSION", "dev"),
        )

    return app
