import logging
from datetime import datetime

from cinema_recs import storage
from cinema_recs.config import Config
from cinema_recs.discord_client import send_notification

logger = logging.getLogger(__name__)


def _build_message(movie_title: str, showtime, reasons: str) -> str:
    lines = [
        f"\U0001F3AC **{movie_title}** is now recommended!",
        f"Next showtime: {showtime.show_date} at {showtime.start_time}",
        f"Why: {reasons}",
    ]
    if showtime.ticket_url:
        lines.append(f"Tickets: {showtime.ticket_url}")
    return "\n".join(lines)


def run_notifications(db_path: str, cinema_id: int, config: Config) -> int:
    """Send a Discord notification the first time each movie's current,
    continuous recommended span begins. Returns the count of notifications
    sent this cycle."""
    if not config.discord_webhook_url or not config.notifications_enabled:
        # FR-007: no webhook configured, or notifications disabled -> never
        # send, and never make a webhook call to find out.
        return 0

    sent = 0
    for title in storage.list_matched_movie_titles(db_path):
        recommendation = storage.get_movie_recommendation(db_path, title)
        record = storage.get_notification_record(db_path, title)
        was_active = record.active if record else False

        if recommendation is None or not recommendation.is_recommended:
            if was_active:
                # Movie dropped out of "recommended" — reset so a later
                # re-entry is treated as a new notification-worthy event
                # (spec FR-003 edge case), not suppressed as a duplicate.
                storage.upsert_notification_record(
                    db_path,
                    title,
                    active=False,
                    last_delivery_outcome=record.last_delivery_outcome if record else None,
                )
            continue

        if was_active:
            # Already notified for this recommended span (spec FR-003/SC-002).
            continue

        showtime = storage.get_next_showtime_for_movie(db_path, cinema_id, title)
        if showtime is None:
            # Recommended but no active showtime to reference yet.
            continue

        message = _build_message(title, showtime, recommendation.reasons)

        try:
            send_notification(config.discord_webhook_url, message)
        except Exception:  # noqa: BLE001 - delivery failure must never block ingestion/recommendation cycles
            logger.exception("Failed to send Discord notification for movie %r", title)
            storage.upsert_notification_record(db_path, title, active=False, last_delivery_outcome="failed")
            continue

        storage.upsert_notification_record(
            db_path, title, active=True, notified_at=datetime.utcnow(), last_delivery_outcome="sent"
        )
        sent += 1
        logger.info("Sent Discord notification for movie %r", title)

    logger.info("Notification evaluation finished: notifications_sent=%d", sent)
    return sent
