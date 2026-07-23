import logging
from datetime import datetime, timezone

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


def _build_cancelled_message(movie_title: str, original_showtime) -> str:
    return "\n".join(
        [
            f"❌ **{movie_title}** showing cancelled",
            f"The {original_showtime.show_date} at {original_showtime.start_time} "
            "showing was removed by the cinema.",
        ]
    )


def _build_rescheduled_message(movie_title: str, original_showtime, new_showtime) -> str:
    lines = [
        f"\U0001F504 **{movie_title}** showing rescheduled",
        f"Was: {original_showtime.show_date} at {original_showtime.start_time}",
        f"Now: {new_showtime.show_date} at {new_showtime.start_time}",
    ]
    if new_showtime.ticket_url:
        lines.append(f"Tickets: {new_showtime.ticket_url}")
    return "\n".join(lines)


def _evaluate_disappearances(db_path: str, cinema_id: int, config: Config) -> int:
    """Follow up on movies already notified as recommended (feature 004):
    when the specific showtime referenced in that notification disappears
    (transitions to 'stale'), send a cancelled or rescheduled alert
    (feature 005 spec FR-001/FR-002/FR-003), at most once per disappearance
    (FR-004), without ever blocking ingestion on delivery failure (FR-007)."""
    alerted = 0
    for record in storage.list_active_notification_records(db_path):
        if record.disappearance_alerted:
            # Already alerted for this showtime's disappearance (FR-004).
            continue

        showtime = storage.get_showtime_by_id(db_path, record.notified_showtime_id)
        if showtime is None or showtime.status != "stale":
            # Still active (or an unexpected missing row) — nothing to alert on yet.
            continue

        replacement = storage.get_next_showtime_for_movie(db_path, cinema_id, record.movie_title)
        if replacement is None:
            message = _build_cancelled_message(record.movie_title, showtime)
        else:
            message = _build_rescheduled_message(record.movie_title, showtime, replacement)

        try:
            send_notification(config.discord_webhook_url, message)
        except Exception:  # noqa: BLE001 - delivery failure must never block ingestion/recommendation cycles
            logger.exception(
                "Failed to send cancellation/reschedule alert for movie %r", record.movie_title
            )
            # Leave state unchanged so the next cycle retries (FR-007).
            continue

        if replacement is None:
            storage.upsert_notification_record(
                db_path,
                record.movie_title,
                active=True,
                notified_at=record.notified_at,
                last_delivery_outcome="sent",
                notified_showtime_id=record.notified_showtime_id,
                disappearance_alerted=True,
            )
            logger.info("Sent cancellation alert for movie %r", record.movie_title)
        else:
            storage.upsert_notification_record(
                db_path,
                record.movie_title,
                active=True,
                notified_at=record.notified_at,
                last_delivery_outcome="sent",
                notified_showtime_id=replacement.id,
                disappearance_alerted=False,
            )
            logger.info("Sent reschedule alert for movie %r", record.movie_title)

        alerted += 1

    return alerted


def run_notifications(db_path: str, cinema_id: int, config: Config) -> int:
    """Send a Discord notification the first time each movie's current,
    continuous recommended span begins, then follow up with a
    cancelled/rescheduled alert if that notified showtime later disappears
    (feature 005). Returns the total count of notifications sent this
    cycle."""
    if not config.discord_webhook_url or not config.notifications_enabled:
        # FR-007/FR-008: no webhook configured, or notifications disabled ->
        # never send, and never make a webhook call to find out.
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
                # Also clears the tracked showtime, since there's no longer
                # a "current" notified showtime to watch for disappearance
                # (feature 005 data-model.md State Transition #5).
                storage.upsert_notification_record(
                    db_path,
                    title,
                    active=False,
                    last_delivery_outcome=record.last_delivery_outcome if record else None,
                    notified_showtime_id=None,
                    disappearance_alerted=False,
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
            db_path,
            title,
            active=True,
            notified_at=datetime.now(timezone.utc).replace(tzinfo=None),
            last_delivery_outcome="sent",
            notified_showtime_id=showtime.id,
            disappearance_alerted=False,
        )
        sent += 1
        logger.info("Sent Discord notification for movie %r", title)

    disappearance_alerts = _evaluate_disappearances(db_path, cinema_id, config)
    sent += disappearance_alerts

    logger.info(
        "Notification evaluation finished: notifications_sent=%d disappearance_alerts_sent=%d",
        sent,
        disappearance_alerts,
    )
    return sent
