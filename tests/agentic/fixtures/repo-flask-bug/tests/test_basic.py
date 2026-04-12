"""Basic tests for user CRUD — these must pass on the initial fixture state."""
import pytest
from app.models import get_user, add_user


def test_get_user_exists():
    db = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    assert get_user(1, db) == {"id": 1, "name": "Alice"}


def test_get_user_missing():
    db = [{"id": 1, "name": "Alice"}]
    assert get_user(99, db) is None


def test_add_user():
    db = []
    user = {"id": 10, "name": "Dave"}
    result = add_user(user, db)
    assert result == {"id": 10, "name": "Dave"}
    assert db == [{"id": 10, "name": "Dave"}]


def test_add_multiple_users():
    db = []
    add_user({"id": 1, "name": "Alice"}, db)
    add_user({"id": 2, "name": "Bob"}, db)
    assert len(db) == 2
