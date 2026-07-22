from flask import Flask, render_template_string

from cinema_recs.config import Config
from cinema_recs.models import Cinema
from cinema_recs.storage import get_latest_ingestion_run, list_active_showtimes

LISTING_TEMPLATE = """
<!doctype html>
<title>{{ cinema.name }} Showtimes</title>
<h1>{{ cinema.name }} Showtimes</h1>
{% if showtimes %}
<table border="1" cellpadding="6">
  <tr><th>Movie</th><th>Date</th><th>Start Time</th><th>Format</th></tr>
  {% for s in showtimes %}
  <tr>
    <td>{{ s.movie_title }}</td>
    <td>{{ s.show_date }}</td>
    <td>{{ s.start_time }}</td>
    <td>{{ s.format or "—" }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p>No showtimes ingested yet.</p>
{% endif %}
<p><a href="/health">Ingestion health</a></p>
"""

HEALTH_TEMPLATE = """
<!doctype html>
<title>Ingestion Health</title>
<h1>Ingestion Health</h1>
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
<p><a href="/">Back to listing</a></p>
"""


def create_app(config: Config, cinema: Cinema) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def listing():
        showtimes = list_active_showtimes(config.db_path, cinema.id)
        return render_template_string(LISTING_TEMPLATE, cinema=cinema, showtimes=showtimes)

    @app.get("/health")
    def health():
        run = get_latest_ingestion_run(config.db_path, cinema.id)
        return render_template_string(HEALTH_TEMPLATE, run=run)

    return app
