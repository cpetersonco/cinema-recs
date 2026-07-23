from unittest.mock import Mock, patch

import pytest
import requests

from cinema_recs.discord_client import send_notification


@patch("cinema_recs.discord_client.requests.post")
def test_send_notification_posts_content_payload(mock_post):
    mock_post.return_value = Mock(status_code=204, raise_for_status=lambda: None)

    send_notification("https://discord.com/api/webhooks/123/abc", "Hello!")

    mock_post.assert_called_once_with(
        "https://discord.com/api/webhooks/123/abc",
        json={"content": "Hello!"},
        timeout=10,
    )


@patch("cinema_recs.discord_client.requests.post")
def test_send_notification_raises_on_non_2xx(mock_post):
    response = Mock(status_code=404)
    response.raise_for_status.side_effect = requests.HTTPError("404 error")
    mock_post.return_value = response

    with pytest.raises(requests.HTTPError):
        send_notification("https://discord.com/api/webhooks/123/abc", "Hello!")


@patch("cinema_recs.discord_client.requests.post")
def test_send_notification_raises_on_connection_error(mock_post):
    mock_post.side_effect = requests.ConnectionError("boom")

    with pytest.raises(requests.ConnectionError):
        send_notification("https://discord.com/api/webhooks/123/abc", "Hello!")
