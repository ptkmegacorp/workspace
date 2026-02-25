"""Example smoke-test for telegram_delivery.send_transcript."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from textwrap import dedent
from unittest import mock

import telegram_delivery


def _make_payload() -> dict[str, object]:
    transcript = """
        This is a long transcript that should be truncated when we format the message. It contains more than
        200 characters so the helper can demonstrate that we only send a short excerpt via Telegram.
    """
    return {
        "clip_id": "test-clip-123",
        "timestamp": "2024-01-01T00:00:00Z",
        "text": dedent(transcript).strip().replace("\n", " "),
        "confidence": 0.87,
    }


def run_test() -> None:
    """Run the helper against a mocked requests.post and validate logging/formatting."""
    os.environ["TELEGRAM_BOT_TOKEN"] = "fake-token"
    os.environ["TELEGRAM_CHAT_ID"] = "123456789"

    payload = _make_payload()
    tmpdir = Path(tempfile.mkdtemp())
    log_file = tmpdir / "delivery.log"
    telegram_delivery.LOG_PATH = log_file

    fake_response = mock.Mock(status_code=200, ok=True, text='{"ok":true}')
    fake_response.raise_for_status = mock.Mock()

    def _fake_post(url: str, json: dict[str, object], timeout: int) -> mock.Mock:
        assert url.endswith("/sendMessage"), "Calls Telegram sendMessage endpoint"
        assert "fake-token" in url, "Uses the configured bot token"
        assert json["chat_id"] == "123456789"
        assert "Clip: test-clip-123" in json["text"]
        assert "When: 2024-01-01T00:00:00Z" in json["text"]
        assert "Excerpt:" in json["text"], "Includes a short excerpt"
        return fake_response

    with mock.patch("telegram_delivery.requests.post", side_effect=_fake_post) as mock_post:
        response = telegram_delivery.send_transcript(payload)

    assert response is fake_response
    assert mock_post.call_count == 1

    assert log_file.exists(), "Delivery log should be created"
    line = log_file.read_text(encoding="utf-8").strip()
    entry = json.loads(line)
    assert entry["clip_id"] == "test-clip-123"
    assert entry["status"] == 200
    assert entry["ok"] is True
    assert entry["confidence"] == 0.87

    print("test_telegram_delivery: PASSED")


if __name__ == "__main__":
    run_test()
