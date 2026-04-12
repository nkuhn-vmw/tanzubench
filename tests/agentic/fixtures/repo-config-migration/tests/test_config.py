"""Config tests — test_load_yaml_config FAILS on initial fixture state."""
import os
import pytest


def test_load_yaml_config(tmp_path):
    """load_config() must read values from a YAML file."""
    from myapp.config import load_config

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "db_host: yaml-host\n"
        "db_port: 9999\n"
        "db_name: yaml_db\n"
        "secret_key: yaml-secret\n"
        "debug: false\n"
    )
    cfg = load_config(str(cfg_file))
    assert cfg["db_host"] == "yaml-host"
    assert cfg["db_port"] == 9999
    assert cfg["db_name"] == "yaml_db"


def test_load_yaml_config_missing_key_falls_back_to_env(tmp_path, monkeypatch):
    """If a key is absent from YAML, fall back to env var."""
    from myapp.config import load_config

    monkeypatch.setenv("DB_HOST", "env-host")
    cfg_file = tmp_path / "config.yaml"
    # db_host intentionally absent
    cfg_file.write_text("db_port: 5432\ndb_name: myapp\nsecret_key: s\ndebug: false\n")
    cfg = load_config(str(cfg_file))
    assert cfg["db_host"] == "env-host"


def test_load_config_file_in_repo():
    """config.yaml must exist at repo root and be loadable."""
    import os
    from myapp.config import load_config

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(repo_root, "config.yaml")
    assert os.path.isfile(cfg_path), "config.yaml missing from repo root"
    cfg = load_config(cfg_path)
    assert "db_host" in cfg
