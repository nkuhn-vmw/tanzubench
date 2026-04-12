# flask-bug-demo

A simplified user-management app demonstrating a search bug.

## Structure

- `app/models.py` — data access layer (find_users, get_user, add_user)
- `app/routes.py` — route handlers (delegate to models)
- `app/utils.py` — pagination and formatting helpers
- `config.py` — app settings
- `tests/` — pytest suite

## Running tests

```
python3 -m pip install pytest
python3 -m pytest tests/ -q
```

## Known issue

`find_users()` in `app/models.py` uses exact string equality (`==`) for search.
It should perform a case-insensitive partial match so that searching for "ali"
returns users named "Alice" or "Alicia".
