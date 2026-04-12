"""Utility helpers for the app."""


def paginate(items, page=1, per_page=10):
    """Return a slice of *items* for the given page."""
    start = (page - 1) * per_page
    return items[start: start + per_page]


def sanitize(text):
    """Strip leading/trailing whitespace and lowercase."""
    return text.strip().lower()


def format_user(user):
    """Return a display string for a user dict."""
    return f"[{user['id']}] {user['name']}"
