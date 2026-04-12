"""Import command — reads data from a file."""
from cli.formatters import format_record


def _validate_input(data):
    """Validate input data before import.

    Returns (True, None) on success, (False, error_message) on failure.
    Duplicated from cmd_export._validate_input — extract to cli.validators!
    """
    if not isinstance(data, dict):
        return False, "data must be a dict"
    if "id" not in data:
        return False, "missing required field: id"
    if not isinstance(data.get("id"), int):
        return False, "field 'id' must be an integer"
    if "name" not in data:
        return False, "missing required field: name"
    if not isinstance(data.get("name"), str):
        return False, "field 'name' must be a string"
    if len(data["name"].strip()) == 0:
        return False, "field 'name' must not be blank"
    if "value" not in data:
        return False, "missing required field: value"
    if data["value"] < 0:
        return False, "field 'value' must be non-negative"
    return True, None


def run_import(args, data=None):
    """Import and validate data from a source."""
    if data is None:
        data = {}
    ok, err = _validate_input(data)
    if not ok:
        return {"status": "error", "message": err}
    line = format_record(data)
    return {"status": "ok", "output": line}
