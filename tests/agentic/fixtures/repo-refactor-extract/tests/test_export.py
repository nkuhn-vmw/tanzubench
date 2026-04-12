"""Export command tests — pass on initial fixture state."""
from cli.cmd_export import run_export


def test_export_valid():
    data = {"id": 1, "name": "Alice", "value": 42}
    result = run_export([], data)
    assert result["status"] == "ok"
    assert "Alice" in result["output"]


def test_export_missing_id():
    data = {"name": "Alice", "value": 42}
    result = run_export([], data)
    assert result["status"] == "error"
    assert "id" in result["message"]


def test_export_negative_value():
    data = {"id": 1, "name": "Alice", "value": -1}
    result = run_export([], data)
    assert result["status"] == "error"
    assert "non-negative" in result["message"]


def test_export_blank_name():
    data = {"id": 1, "name": "   ", "value": 0}
    result = run_export([], data)
    assert result["status"] == "error"
    assert "blank" in result["message"]
