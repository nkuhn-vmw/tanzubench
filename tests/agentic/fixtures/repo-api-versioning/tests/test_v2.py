"""v2 API tests — FAIL on initial fixture state (api/v2 doesn't exist yet)."""
import pytest


def test_v2_module_exists():
    """api.v2.users must be importable."""
    from api.v2 import users  # noqa: F401


def test_v2_get_users_returns_list():
    from api.v2.users import get_users
    users = get_users()
    assert isinstance(users, list)
    assert len(users) >= 1


def test_v2_users_have_email():
    """v2 users must include an email field."""
    from api.v2.users import get_users
    for u in get_users():
        assert "email" in u
        assert "@" in u["email"]


def test_v2_users_have_id_and_name():
    from api.v2.users import get_users
    for u in get_users():
        assert "id" in u
        assert "name" in u


def test_router_v2_users():
    """Router must handle /v2/users."""
    from api.router import dispatch
    result = dispatch("/v2/users")
    assert isinstance(result, list)
    assert "email" in result[0]
