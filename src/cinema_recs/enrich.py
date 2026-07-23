import logging

from cinema_recs import storage
from cinema_recs.tmdb_client import (
    MatchResult,
    get_movie_details,
    match_title,
    search_movie,
    strip_event_suffix,
    strip_promo_price_prefix,
)

logger = logging.getLogger(__name__)


def _candidate_titles(title: str) -> list[str]:
    """The raw title first, then an event-suffix-stripped variant if that
    actually changes anything — repertory venues sometimes append an event
    descriptor (" + Costume Contest", "(EVANGELION 30th Movie Fest)") onto
    an otherwise-real, matchable title (tmdb_client.strip_event_suffix)."""
    candidates = [title]
    cleaned = strip_event_suffix(title)
    if cleaned and cleaned != title:
        candidates.append(cleaned)
    return candidates


def run_enrichment(db_path: str, tmdb_api_key: str) -> int:
    """Enrich every distinct movie title with no movie_metadata row yet
    (spec FR-002/FR-003's caching requirement). Returns the count attempted."""
    titles = storage.list_distinct_movie_titles_without_metadata(db_path)

    for title in titles:
        try:
            match = MatchResult(status="unmatched")
            for candidate in _candidate_titles(title):
                results = search_movie(tmdb_api_key, strip_promo_price_prefix(candidate))
                match = match_title(candidate, results)
                if match.status == "matched":
                    break
        except Exception as exc:  # noqa: BLE001 - enrichment failures must not break ingestion
            logger.exception("Enrichment lookup failed for movie %r", title)
            storage.record_enrichment_attempt(db_path, title, outcome="failed", error_message=str(exc))
            continue

        if match.status == "matched":
            try:
                details = get_movie_details(tmdb_api_key, match.tmdb_id)
            except Exception as exc:  # noqa: BLE001 - same as above
                logger.exception("Enrichment detail fetch failed for movie %r", title)
                storage.record_enrichment_attempt(db_path, title, outcome="failed", error_message=str(exc))
                continue

            storage.upsert_movie_metadata(
                db_path,
                movie_title=title,
                match_status="matched",
                tmdb_id=details.tmdb_id,
                tmdb_title=details.title,
                genres=", ".join(details.genres) if details.genres else None,
                overview=details.overview,
                release_year=details.release_year,
                average_rating=details.average_rating,
                runtime_minutes=details.runtime_minutes,
                poster_path=details.poster_path,
            )
            storage.record_enrichment_attempt(db_path, title, outcome="matched")
            logger.info("Enriched movie %r with TMDB id %s", title, details.tmdb_id)
        else:
            # "unmatched" and "ambiguous" both get recorded as an explicit
            # unmatched MovieMetadata row (spec FR-004/US2) so the listing
            # view can distinguish "attempted but unmatched" from "not yet
            # attempted", never guessing at fabricated metadata.
            storage.upsert_movie_metadata(db_path, movie_title=title, match_status="unmatched")
            storage.record_enrichment_attempt(db_path, title, outcome="unmatched")
            logger.info("No confident TMDB match for movie %r", title)

    return len(titles)
