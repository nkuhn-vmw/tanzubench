"""v1 API tests — pass on initial fixture state."""
from api.v1.users import get_users, get_user
from api.router import dispatch


def test_v1_get_users_returns_list():
    users = get_users()
    assert isinstance(users, list)
    assert len(users) == 2


def test_v1_users_have_id_and_name():
    for u in get_users():
        assert "id" in u
        assert "name" in u


def test_v1_users_no_email():
    """v1 users must NOT expose email."""
    for u in get_users():
        assert "email" not in u


def test_v1_get_user_found():
    u = get_user(1)
    assert u is not None
    assert u["name"] == "Alice"


def test_v1_get_user_not_found():
    assert get_user(999) is None


def test_router_v1_users():
    result = dispatch("/v1/users")
    assert isinstance(result, list)
    assert result[0]["name"] == "Alice"
