"""API v1 — users resource."""


def get_users():
    """Return the v1 user list (id + name only)."""
    return [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]


def get_user(user_id):
    """Return a single v1 user by id, or None."""
    for u in get_users():
        if u["id"] == user_id:
            return u
    return None
