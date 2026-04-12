"""Application configuration — reads from environment variables.

TODO: migrate to YAML-based config with env var fallback.
Expected interface after migration:
    load_config(path) -> dict   reads YAML, falls back to env vars
"""
import os

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
DB_NAME = os.environ.get("DB_NAME", "myapp")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
