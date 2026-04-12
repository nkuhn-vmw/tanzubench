"""Output formatters for CLI commands."""


def format_record(data):
    """Format a data dict as a single display line."""
    return f"id={data['id']} name={data['name']!r} value={data['value']}"


def format_error(message):
    """Format an error message for display."""
    return f"ERROR: {message}"


def format_summary(records):
    """Format a list of records as a summary line."""
    return f"{len(records)} record(s) processed"
