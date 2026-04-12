"""Request handlers — may reference config values."""
from myapp.config import SECRET_KEY, DEBUG


def handle_request(path, headers=None):
    """Stub handler that returns a response dict."""
    if headers is None:
        headers = {}
    return {
        "path": path,
        "debug": DEBUG,
        "auth": headers.get("Authorization") == f"Bearer {SECRET_KEY}",
    }


def health():
    """Simple health endpoint."""
    return {"status": "ok"}
