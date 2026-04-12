"""Search tests — test_search_partial_match FAILS on initial fixture state."""
import pytest
from app.models import find_users


def test_search_exact_match():
    db = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    # Exact match still works in the broken version
    result = find_users("Alice", db)
    assert result == [{"id": 1, "name": "Alice"}]


def test_search_no_match():
    db = [{"id": 1, "name": "Alice"}]
    result = find_users("Zara", db)
    assert result == []


def test_search_partial_match():
    """Partial/case-insensitive search: 'ali' should match 'Alice'."""
    db = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    result = find_users("ali", db)
    assert result == [{"id": 1, "name": "Alice"}]


def test_search_case_insensitive():
    """Uppercase query should match lowercase name."""
    db = [{"id": 1, "name": "alice"}, {"id": 2, "name": "Bob"}]
    result = find_users("ALICE", db)
    assert result == [{"id": 1, "name": "alice"}]


def test_search_substring():
    """Substring match across multiple users."""
    db = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Alicia"}, {"id": 3, "name": "Bob"}]
    result = find_users("ali", db)
    assert len(result) == 2
