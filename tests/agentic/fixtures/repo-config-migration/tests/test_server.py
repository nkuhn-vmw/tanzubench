"""Server tests — pass on the initial fixture state."""
import os
import pytest
from unittest.mock import patch


def test_get_dsn_default():
    """DSN is built from default env-var values."""
    from myapp.server import get_dsn
    dsn = get_dsn()
    assert "localhost" in dsn
    assert "5432" in dsn
    assert "myapp" in dsn


def test_get_dsn_custom_env(monkeypatch):
    """Custom env vars flow into the DSN."""
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_NAME", "testdb")
    # Re-import to pick up monkeypatched env (import already cached, patch module attrs)
    import myapp.config as cfg
    import importlib
    importlib.reload(cfg)
    import myapp.server as srv
    importlib.reload(srv)
    dsn = srv.get_dsn()
    assert "db.example.com" in dsn
    assert "5433" in dsn


def test_is_ready():
    from myapp.server import is_ready
    assert is_ready() is True
