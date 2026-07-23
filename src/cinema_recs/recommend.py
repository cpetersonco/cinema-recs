import logging

from cinema_recs import storage
from cinema_recs.config import Config
from cinema_recs.letterboxd_client import (
    BUILT_IN_BEST_OF_LISTS,
    fetch_best_of_list_slugs,
    fetch_movie_rating,
    fetch_watchlist_slugs,
    resolve_letterboxd_slug,
)

logger = logging.getLogger(__name__)


def _refresh_reference_lists(db_path: str, config: Config) -> None:
    if config.letterboxd_username:
        try:
            slugs = fetch_watchlist_slugs(config.letterboxd_username)
            storage.replace_reference_list_slugs(db_path, "watchlist", slugs)
            logger.info("Refreshed watchlist cache: %d film(s)", len(slugs))
        except Exception:  # noqa: BLE001 - keep the previously cached watchlist, don't treat as empty
            logger.exception("Failed to refresh Letterboxd watchlist; keeping previously cached data")

    for list_key, best_of_list in BUILT_IN_BEST_OF_LISTS.items():
        try:
            slugs = fetch_best_of_list_slugs(best_of_list.url)
            storage.replace_reference_list_slugs(db_path, f"best_of:{list_key}", slugs)
            logger.info("Refreshed best-of list %r cache: %d film(s)", list_key, len(slugs))
        except Exception:  # noqa: BLE001 - keep the previously cached list, don't treat as empty
            logger.exception("Failed to refresh Letterboxd best-of list %r; keeping previously cached data", list_key)


def _ensure_letterboxd_data_cached(db_path: str) -> None:
    for title in storage.list_distinct_matched_movie_titles_without_letterboxd_data(db_path):
        metadata = storage.get_movie_metadata(db_path, title)

        try:
            slug = resolve_letterboxd_slug(metadata.tmdb_id)
        except Exception:  # noqa: BLE001 - transient failure; retry next cycle rather than caching a false negative
            logger.exception("Failed to resolve Letterboxd slug for movie %r; will retry next cycle", title)
            continue

        rating = None
        if slug is not None:
            try:
                rating = fetch_movie_rating(slug)
            except Exception:  # noqa: BLE001 - cache the resolved slug even if the rating fetch failed
                logger.exception("Failed to fetch Letterboxd rating for movie %r", title)

        storage.upsert_letterboxd_movie_data(db_path, title, metadata.tmdb_id, slug, rating)


def run_recommendation_evaluation(db_path: str, config: Config) -> int:
    """Evaluate every feature-002-matched movie against the configured
    Letterboxd criteria (watchlist / rating / best-of list) and store its
    recommendation status. Returns the count of movies evaluated."""
    any_criterion_configured = bool(config.letterboxd_username) or config.letterboxd_rating_threshold is not None
    matched_titles = storage.list_matched_movie_titles(db_path)

    if not any_criterion_configured:
        # FR-005/SC-004: zero configuration means zero recommendations,
        # without attempting any Letterboxd requests.
        for title in matched_titles:
            storage.upsert_movie_recommendation(db_path, title, is_recommended=False, reasons=None)
        logger.info("No Letterboxd criteria configured; marked %d movie(s) not recommended", len(matched_titles))
        return len(matched_titles)

    _refresh_reference_lists(db_path, config)
    _ensure_letterboxd_data_cached(db_path)

    watchlist_slugs = storage.get_reference_list_slugs(db_path, "watchlist") if config.letterboxd_username else set()
    best_of_slug_sets = {
        list_key: storage.get_reference_list_slugs(db_path, f"best_of:{list_key}")
        for list_key in BUILT_IN_BEST_OF_LISTS
    }

    for title in matched_titles:
        lb_data = storage.get_letterboxd_movie_data(db_path, title)

        if lb_data is None or lb_data.letterboxd_slug is None:
            # No resolvable Letterboxd entry — none of the three criteria
            # can be evaluated with confidence (spec FR-004).
            storage.upsert_movie_recommendation(db_path, title, is_recommended=False, reasons=None)
            continue

        reasons = []
        if config.letterboxd_username and lb_data.letterboxd_slug in watchlist_slugs:
            reasons.append("watchlist")
        if (
            config.letterboxd_rating_threshold is not None
            and lb_data.average_rating is not None
            and lb_data.average_rating > config.letterboxd_rating_threshold
        ):
            reasons.append("rating")
        for list_key, slugs in best_of_slug_sets.items():
            if lb_data.letterboxd_slug in slugs:
                reasons.append(BUILT_IN_BEST_OF_LISTS[list_key].display_name)

        storage.upsert_movie_recommendation(
            db_path,
            title,
            is_recommended=bool(reasons),
            reasons=",".join(reasons) if reasons else None,
        )

    logger.info("Recommendation evaluation finished: movies_evaluated=%d", len(matched_titles))
    return len(matched_titles)
