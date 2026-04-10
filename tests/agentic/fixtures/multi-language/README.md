# multi-language

`app.py` has a `get_response()` function that returns a dict. The JavaScript
frontend that consumes this endpoint expects the response key to be `"data"`,
but the current implementation returns `"result"`.

## Task

Fix `app.py` so that `get_response()` returns `{"data": 42}`. The Python tests
in `tests/` must pass when you are done.
