"""Tests for shared validation logic in cli.validators — FAIL on initial fixture state."""
import pytest


def _get_validate_input():
    """Lazy import so collection doesn't fail before the agent adds the function."""
    from cli.validators import validate_input  # noqa: PLC0415
    return validate_input


def test_validate_valid_record():
    validate_input = _get_validate_input()
    ok, err = validate_input({"id": 1, "name": "Alice", "value": 10})
    assert ok is True
    assert err is None


def test_validate_missing_id():
    validate_input = _get_validate_input()
    ok, err = validate_input({"name": "Alice", "value": 10})
    assert ok is False
    assert "id" in err


def test_validate_missing_name():
    validate_input = _get_validate_input()
    ok, err = validate_input({"id": 1, "value": 10})
    assert ok is False
    assert "name" in err


def test_validate_negative_value():
    validate_input = _get_validate_input()
    ok, err = validate_input({"id": 1, "name": "Alice", "value": -5})
    assert ok is False
    assert "non-negative" in err


def test_validate_blank_name():
    validate_input = _get_validate_input()
    ok, err = validate_input({"id": 1, "name": "  ", "value": 0})
    assert ok is False
    assert "blank" in err


def test_validate_not_dict():
    validate_input = _get_validate_input()
    ok, err = validate_input("not a dict")
    assert ok is False
    assert "dict" in err
