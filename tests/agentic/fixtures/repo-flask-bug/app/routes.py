"""Route handlers — thin layer that delegates to models."""
from app.models import find_users, get_user, add_user


def search_users(query, users_db=None):
    """Handle GET /users?q=<query>."""
    return find_users(query, users_db)


def fetch_user(user_id, users_db=None):
    """Handle GET /users/<id>."""
    return get_user(user_id, users_db)


def create_user(user, users_db=None):
    """Handle POST /users."""
    return add_user(user, users_db)
