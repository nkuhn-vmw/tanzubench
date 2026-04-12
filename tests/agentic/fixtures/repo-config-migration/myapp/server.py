"""Minimal server — uses config values from myapp.config."""
from myapp.config import DB_HOST, DB_PORT, DB_NAME


def get_dsn():
    """Return a database connection string."""
    return f"postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"


def is_ready():
    """Health check — always True in this stub."""
    return True
