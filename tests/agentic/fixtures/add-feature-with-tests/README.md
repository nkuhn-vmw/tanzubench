# add-feature-with-tests

`app.py` exposes a simple in-memory item store with `get_items()` and `add_item(item)`.

## Task

`test_pagination` in `tests/test_app.py` already exists but the test currently
fails because `get_items()` does not accept pagination arguments yet.

Add `page` and `per_page` parameters to `get_items()` so the function returns
the correct slice of items. When no arguments are passed it should return all
items (existing behaviour must be preserved).

All tests in `tests/` must pass when you are done.
