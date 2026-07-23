from flask import Flask, render_template_string

from cinema_recs.config import Config
from cinema_recs.models import Cinema
from cinema_recs.storage import (
    get_latest_ingestion_run,
    get_movie_metadata,
    get_movie_recommendation,
    list_active_showtimes,
)

TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p/w200"

LISTING_TEMPLATE = """
<!doctype html>
<title>Showtimes</title>
{% for section in cinema_sections %}
<h1>{{ section.cinema.name }} Showtimes</h1>
{% if section.showtimes %}
<table border="1" cellpadding="6">
  <tr><th>Movie</th><th>Date</th><th>Start Time</th><th>Format</th><th>Genre</th><th>Rating</th><th>Poster</th><th>Recommended</th></tr>
  {% for s in section.showtimes %}
  {% set recommendation = section.recommendations.get(s.movie_title) %}
  <tr{% if recommendation and recommendation.is_recommended %} style="background-color: #fff3cd;"{% endif %}>
    <td>{{ s.movie_title }}</td>
    <td>{{ s.show_date }}</td>
    <td>{{ s.start_time }}</td>
    <td>{{ s.format or "—" }}</td>
    {% set metadata = section.metadata.get(s.movie_title) %}
    {% if metadata and metadata.match_status == "matched" %}
    <td>{{ metadata.genres or "—" }}</td>
    <td>{{ metadata.average_rating or "—" }}</td>
    <td>
      {% if metadata.poster_path %}
      <img src="{{ poster_base_url }}{{ metadata.poster_path }}" alt="{{ s.movie_title }} poster" height="60">
      {% else %}
      —
      {% endif %}
    </td>
    {% else %}
    <td>—</td>
    <td>—</td>
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


def create_app(config: Config, cinemas: list[Cinema]) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def listing():
        cinema_sections = []
        for cinema in cinemas:
            showtimes = list_active_showtimes(config.db_path, cinema.id)
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
                }
            )
        return render_template_string(
            LISTING_TEMPLATE,
            cinema_sections=cinema_sections,
            poster_base_url=TMDB_POSTER_BASE_URL,
        )

    @app.get("/health")
    def health():
        cinema_runs = [
            {"cinema": cinema, "run": get_latest_ingestion_run(config.db_path, cinema.id)}
            for cinema in cinemas
        ]
        return render_template_string(HEALTH_TEMPLATE, cinema_runs=cinema_runs)

    return app
