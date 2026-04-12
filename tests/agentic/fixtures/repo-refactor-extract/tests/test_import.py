"""Import command tests — pass on initial fixture state."""
from cli.cmd_import import run_import


def test_import_valid():
    data = {"id": 2, "name": "Bob", "value": 7}
    result = run_import([], data)
    assert result["status"] == "ok"
    assert "Bob" in result["output"]


def test_import_missing_name():
    data = {"id": 2, "value": 7}
    result = run_import([], data)
    assert result["status"] == "error"
    assert "name" in result["message"]


def test_import_id_not_int():
    data = {"id": "two", "name": "Bob", "value": 7}
    result = run_import([], data)
    assert result["status"] == "error"
    assert "integer" in result["message"]


def test_import_not_dict():
    result = run_import([], data="bad")
    assert result["status"] == "error"
