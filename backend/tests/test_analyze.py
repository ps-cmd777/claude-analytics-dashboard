"""Tests for the GET /api/analyze/{session_id} SSE endpoint.

All tests mock the anthropic.Anthropic client — no real API calls are made.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app
from services.profiler import DataProfiler, DataProfile, ColumnProfile
from services.session_store import _sessions, create_session


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
def sample_profile() -> DataProfile:
    """A minimal DataProfile for testing."""
    age_cp = ColumnProfile(
        name="age", dtype="int64", missing_count=0, missing_pct=0.0,
        unique_count=3, mean=30.0, median=30.0, std=5.0,
        min_val=25.0, max_val=35.0, q25=27.5, q75=32.5,
    )
    name_cp = ColumnProfile(
        name="name", dtype="object", missing_count=0, missing_pct=0.0,
        unique_count=3, top_values={"Alice": 1, "Bob": 1},
    )
    return DataProfile(
        shape=(3, 2), columns=["name", "age"],
        column_profiles={"name": name_cp, "age": age_cp},
        numeric_columns=["age"], categorical_columns=["name"], date_columns=[],
        total_missing=0, total_missing_pct=0.0, correlation_matrix={},
        duplicate_rows=0, memory_usage_mb=0.001,
    )


@pytest.fixture()
def session(sample_profile, tmp_path):
    """Create a session and return the Session object (has session_id + session_token)."""
    df = pd.DataFrame({"name": ["Alice", "Bob", "Carol"], "age": [30, 25, 35]})
    csv_path = tmp_path / "test.csv"
    df.to_csv(csv_path, index=False)
    profiler = DataProfiler()
    profiler.load_csv(csv_path)
    profiler.profile()
    return create_session("test.csv", df, profiler, sample_profile)


# ---------------------------------------------------------------------------
# Mock helpers (same pattern as Project 1's test_analyzer.py)
# ---------------------------------------------------------------------------


def _make_text_block(text: str) -> MagicMock:
    """Create a mock ContentBlock with text."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(name: str, tool_id: str, input_data: dict) -> MagicMock:
    """Create a mock ContentBlock for a tool_use call."""
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = input_data
    return block


def _make_mock_response(content: list, stop_reason: str) -> MagicMock:
    """Create a mock Anthropic Messages response."""
    resp = MagicMock()
    resp.content = content
    resp.stop_reason = stop_reason
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_analyze_unknown_session_returns_404(client):
    """Requesting analysis for a non-existent session returns HTTP 404."""
    response = client.get("/api/analyze/nonexistent-session-id")
    assert response.status_code == 404


def test_analyze_streams_status_and_done_events(client, session):
    """Analysis endpoint emits status events, token events, and a done event."""
    final_text = (
        "## EXECUTIVE_SUMMARY ##\nGreat dataset.\n"
        "## KEY_FINDINGS ##\n1. Finding one.\n"
        "## COLUMN_ANALYSES ##\n### age\nSummary: Numeric.\nQuality: Good.\nPatterns: Normal.\n"
        "## ANOMALIES ##\n- None.\n"
        "## RECOMMENDATIONS ##\n1. Do more analysis.\n"
        "## METHODOLOGY ##\nUsed tools.\n"
    )

    mock_response = _make_mock_response(
        content=[_make_text_block(final_text)],
        stop_reason="end_turn",
    )

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    cookies = {"session_token": session.session_token}

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        with client.stream("GET", f"/api/analyze/{session.session_id}", cookies=cookies) as response:
            assert response.status_code == 200
            body = response.read().decode()

    assert '"type": "status"' in body
    assert '"type": "token"' in body
    assert '"type": "done"' in body


def test_analyze_done_event_contains_result(client, session):
    """The done SSE event contains a structured AnalysisResult JSON payload."""
    final_text = (
        "## EXECUTIVE_SUMMARY ##\nThis is a great dataset with 3 rows.\n"
        "## KEY_FINDINGS ##\n1. Age ranges from 25 to 35.\n"
        "## COLUMN_ANALYSES ##\n### age\nSummary: Age column.\nQuality: Good.\nPatterns: Normal distribution.\n"
        "## ANOMALIES ##\n- No anomalies found.\n"
        "## RECOMMENDATIONS ##\n1. Collect more data.\n"
        "## METHODOLOGY ##\nUsed profiling tools.\n"
    )

    mock_response = _make_mock_response(
        content=[_make_text_block(final_text)],
        stop_reason="end_turn",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    cookies = {"session_token": session.session_token}

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        with client.stream("GET", f"/api/analyze/{session.session_id}", cookies=cookies) as response:
            body = response.read().decode()

    done_lines = [
        line for line in body.split("\n")
        if line.startswith("data:") and '"type": "done"' in line
    ]
    assert len(done_lines) > 0

    done_payload = json.loads(done_lines[0][len("data: "):])
    assert done_payload["type"] == "done"
    assert done_payload["result"] is not None
    assert "executive_summary" in done_payload["result"]
    assert "key_findings" in done_payload["result"]


def test_analyze_stores_result_in_session(client, session):
    """After analysis, session.analysis is populated in the session store."""
    from services.session_store import get_session

    final_text = (
        "## EXECUTIVE_SUMMARY ##\nGreat dataset.\n"
        "## KEY_FINDINGS ##\n1. Finding.\n"
        "## COLUMN_ANALYSES ##\n### age\nSummary: Numeric.\nQuality: Good.\nPatterns: Normal.\n"
        "## ANOMALIES ##\n- None.\n"
        "## RECOMMENDATIONS ##\n1. Recommend.\n"
        "## METHODOLOGY ##\nTools used.\n"
    )

    mock_response = _make_mock_response(
        content=[_make_text_block(final_text)],
        stop_reason="end_turn",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    cookies = {"session_token": session.session_token}

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        with client.stream("GET", f"/api/analyze/{session.session_id}", cookies=cookies) as response:
            response.read()

    s = get_session(session.session_id)
    assert s is not None
    assert s.analysis is not None
    assert "great dataset" in s.analysis.executive_summary.lower()


def test_analyze_with_tool_use_iteration(client, session):
    """Analysis handles one tool-use iteration before returning end_turn."""
    tool_response = _make_mock_response(
        content=[_make_tool_use_block("get_correlations", "tool-1", {})],
        stop_reason="tool_use",
    )
    final_text = (
        "## EXECUTIVE_SUMMARY ##\nAnalyzed after tool use.\n"
        "## KEY_FINDINGS ##\n1. Correlations checked.\n"
        "## COLUMN_ANALYSES ##\n### age\nSummary: Age.\nQuality: Good.\nPatterns: Normal.\n"
        "## ANOMALIES ##\n- None.\n"
        "## RECOMMENDATIONS ##\n1. Proceed.\n"
        "## METHODOLOGY ##\nUsed get_correlations.\n"
    )
    final_response = _make_mock_response(
        content=[_make_text_block(final_text)],
        stop_reason="end_turn",
    )

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [tool_response, final_response]
    cookies = {"session_token": session.session_token}

    with patch("services.claude_client.anthropic.Anthropic", return_value=mock_client):
        with client.stream("GET", f"/api/analyze/{session.session_id}", cookies=cookies) as response:
            body = response.read().decode()

    assert mock_client.messages.create.call_count == 2
    assert '"type": "done"' in body
