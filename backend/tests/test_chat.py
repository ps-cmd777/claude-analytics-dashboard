"""Tests for the POST /api/chat/{session_id} SSE endpoint.

All tests mock the anthropic.Anthropic client — no real API calls are made.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app
from services.profiler import DataProfiler
from services.session_store import _sessions, create_session, get_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_sessions():
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def session_id(tmp_path) -> str:
    """Create a test session and return its ID."""
    df = pd.DataFrame({"sales": [100, 200, 300], "region": ["East", "West", "North"]})
    csv_path = tmp_path / "sales.csv"
    df.to_csv(csv_path, index=False)

    profiler = DataProfiler()
    profiler.load_csv(csv_path)
    profile = profiler.profile()

    session = create_session("sales.csv", df, profiler, profile)
    return session.session_id


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_mock_response(content: list, stop_reason: str) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.stop_reason = stop_reason
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_chat_unknown_session_returns_404(client):
    """Chatting with a non-existent session returns HTTP 404."""
    response = client.post(
        "/api/chat/nonexistent-session-id",
        json={"message": "Hello"},
    )
    assert response.status_code == 404


def test_chat_streams_tokens(client, session_id):
    """Chat endpoint emits token SSE events for the reply text."""
    reply_text = "The average sales is 200."

    mock_response = _make_mock_response(
        content=[_make_text_block(reply_text)],
        stop_reason="end_turn",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        with client.stream(
            "POST",
            f"/api/chat/{session_id}",
            json={"message": "What is the average sales?"},
        ) as response:
            assert response.status_code == 200
            body = response.read().decode()

    assert '"type": "token"' in body
    assert '"type": "done"' in body

    # Reconstruct the reply from token events
    token_texts = []
    for line in body.split("\n"):
        if line.startswith("data:"):
            payload = json.loads(line[len("data: "):])
            if payload["type"] == "token":
                token_texts.append(payload["text"])
    full_reply = "".join(token_texts)
    assert "200" in full_reply


def test_chat_appends_to_history(client, session_id):
    """After chatting, the session's chat_history has the user + assistant turns."""
    reply_text = "East region leads in sales."

    mock_response = _make_mock_response(
        content=[_make_text_block(reply_text)],
        stop_reason="end_turn",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        with client.stream(
            "POST",
            f"/api/chat/{session_id}",
            json={"message": "Which region has the highest sales?"},
        ) as response:
            response.read()

    session = get_session(session_id)
    assert session is not None
    assert len(session.chat_history) == 2
    assert session.chat_history[0]["role"] == "user"
    assert session.chat_history[0]["content"] == "Which region has the highest sales?"
    assert session.chat_history[1]["role"] == "assistant"
    assert "East" in session.chat_history[1]["content"]


def test_chat_multiple_turns_accumulate_history(client, session_id):
    """Multiple chat turns each append to history, maintaining context."""
    reply_text = "Great question!"

    mock_response = _make_mock_response(
        content=[_make_text_block(reply_text)],
        stop_reason="end_turn",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        # First turn
        with client.stream(
            "POST", f"/api/chat/{session_id}", json={"message": "Question 1"}
        ) as r:
            r.read()

        # Second turn
        with client.stream(
            "POST", f"/api/chat/{session_id}", json={"message": "Question 2"}
        ) as r:
            r.read()

    session = get_session(session_id)
    assert session is not None
    assert len(session.chat_history) == 4  # 2 user + 2 assistant


def test_chat_empty_message_rejected(client, session_id):
    """Sending an empty message returns HTTP 422 (Pydantic validation)."""
    response = client.post(
        f"/api/chat/{session_id}",
        json={"message": ""},
    )
    assert response.status_code == 422


def test_chat_done_event_has_no_result(client, session_id):
    """The done SSE event for chat does not include a result field (unlike analyze)."""
    mock_response = _make_mock_response(
        content=[_make_text_block("Some reply.")],
        stop_reason="end_turn",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        with client.stream(
            "POST",
            f"/api/chat/{session_id}",
            json={"message": "Any question?"},
        ) as response:
            body = response.read().decode()

    done_lines = [
        line for line in body.split("\n")
        if line.startswith("data:") and '"type": "done"' in line
    ]
    assert len(done_lines) > 0
    done_payload = json.loads(done_lines[0][len("data: "):])
    assert done_payload["type"] == "done"
    # Chat done event has no 'result' or it's None/absent
    assert done_payload.get("result") is None
