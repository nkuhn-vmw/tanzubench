"""Simple URL router — dispatches paths to handler functions."""
from api.v1 import users as v1_users


def dispatch(path):
    """Route *path* to the appropriate handler and return the result.

    Supported routes:
      GET /v1/users  -> v1_users.get_users()

    TODO: add /v2/users -> v2_users.get_users()
    """
    if path == "/v1/users":
        return v1_users.get_users()
    raise ValueError(f"Unknown route: {path}")
