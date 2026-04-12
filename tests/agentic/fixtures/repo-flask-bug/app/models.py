"""User model and database access layer."""

# In-memory user store (keyed by id)
_users_db = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
    {"id": 3, "name": "Charlie"},
]


def find_users(query, users_db=None):
    """Return users whose name matches *query*.

    BUG: uses exact equality instead of partial/case-insensitive match.
    Expected: find_users("ali") should return [{"id": 1, "name": "Alice"}]
    """
    if users_db is None:
        users_db = _users_db
    return [u for u in users_db if u["name"] == query]


def get_user(user_id, users_db=None):
    """Return a single user by id, or None."""
    if users_db is None:
        users_db = _users_db
    for u in users_db:
        if u["id"] == user_id:
            return u
    return None


def add_user(user, users_db=None):
    """Append a user dict to the store and return it."""
    if users_db is None:
        users_db = _users_db
    users_db.append(user)
    return user
