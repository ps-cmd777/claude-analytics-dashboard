"""Tests for the in-memory session store."""

from __future__ import annotations

import pandas as pd
import pytest

from services.profiler import DataProfiler
from services.session_store import (
    create_session,
    delete_session,
    get_session,
    list_sessions,
    session_count,
    _sessions,
)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear the session store before and after each test."""
    _sessions.clear()
    yield
    _sessions.clear()


@pytest.fixture()
def sample_df() -> pd.DataFrame:
    """A minimal DataFrame for testing."""
    return pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})


@pytest.fixture()
def sample_profiler_and_profile(sample_df, tmp_path):
    """A profiler with a profile computed from the sample DataFrame."""
    csv_path = tmp_path / "test.csv"
    sample_df.to_csv(csv_path, index=False)
    profiler = DataProfiler()
    profiler.load_csv(csv_path)
    profile = profiler.profile()
    return profiler, profile


def test_create_session_returns_session(sample_df, sample_profiler_and_profile):
    """create_session returns a session with a non-empty UUID session_id."""
    profiler, profile = sample_profiler_and_profile
    session = create_session("test.csv", sample_df, profiler, profile)

    assert session.session_id != ""
    assert len(session.session_id) == 36  # UUID4 format
    assert session.filename == "test.csv"
    assert session.profile is profile
    assert session.analysis is None
    assert session.chat_history == []


def test_get_session_retrieves_created_session(sample_df, sample_profiler_and_profile):
    """get_session returns the session after create_session."""
    profiler, profile = sample_profiler_and_profile
    session = create_session("data.csv", sample_df, profiler, profile)

    retrieved = get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id
    assert retrieved.filename == "data.csv"


def test_get_session_returns_none_for_unknown_id():
    """get_session returns None when the session ID does not exist."""
    result = get_session("nonexistent-id-0000-0000-000000000000")
    assert result is None


def test_delete_session_removes_session(sample_df, sample_profiler_and_profile):
    """delete_session removes the session and returns True."""
    profiler, profile = sample_profiler_and_profile
    session = create_session("data.csv", sample_df, profiler, profile)

    deleted = delete_session(session.session_id)
    assert deleted is True
    assert get_session(session.session_id) is None


def test_delete_session_returns_false_for_unknown_id():
    """delete_session returns False when the session ID does not exist."""
    result = delete_session("nonexistent-id-0000-0000-000000000000")
    assert result is False


def test_session_count_reflects_active_sessions(sample_df, sample_profiler_and_profile):
    """session_count returns the correct number of active sessions."""
    profiler, profile = sample_profiler_and_profile
    assert session_count() == 0

    s1 = create_session("a.csv", sample_df, profiler, profile)
    assert session_count() == 1

    create_session("b.csv", sample_df, profiler, profile)
    assert session_count() == 2

    delete_session(s1.session_id)
    assert session_count() == 1


def test_list_sessions_returns_all_ids(sample_df, sample_profiler_and_profile):
    """list_sessions returns all active session IDs."""
    profiler, profile = sample_profiler_and_profile
    s1 = create_session("a.csv", sample_df, profiler, profile)
    s2 = create_session("b.csv", sample_df, profiler, profile)

    ids = list_sessions()
    assert s1.session_id in ids
    assert s2.session_id in ids
    assert len(ids) == 2


def test_session_chat_history_mutable(sample_df, sample_profiler_and_profile):
    """Chat history can be mutated on a retrieved session."""
    profiler, profile = sample_profiler_and_profile
    session = create_session("data.csv", sample_df, profiler, profile)

    retrieved = get_session(session.session_id)
    assert retrieved is not None
    retrieved.chat_history.append({"role": "user", "content": "Hello"})

    same_session = get_session(session.session_id)
    assert same_session is not None
    assert len(same_session.chat_history) == 1
