import requests


def send_notification(webhook_url: str, message: str) -> None:
    """POST a plain-text message to a Discord webhook. Raises on any
    non-2xx response or network error — the caller (notify.py) is
    responsible for catching, logging, and leaving the movie's
    notification_record inactive so the next cycle retries (spec FR-005).
    No in-process retry here — "try again next cycle" is already correct
    per research.md, so a second retry mechanism would be redundant."""
    response = requests.post(webhook_url, json={"content": message}, timeout=10)
    response.raise_for_status()
