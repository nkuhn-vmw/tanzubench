import importlib
import sys


def _fresh_app():
    """Reload app so items list is reset between tests."""
    if "app" in sys.modules:
        del sys.modules["app"]
    return importlib.import_module("app")


def test_add_item():
    app = _fresh_app()
    result = app.add_item("apple")
    assert result == "apple"


def test_get_items():
    app = _fresh_app()
    app.add_item("a")
    app.add_item("b")
    assert app.get_items() == ["a", "b"]


def test_pagination():
    app = _fresh_app()
    for i in range(1, 6):
        app.add_item(f"item{i}")
    # page=2, per_page=2 should return items 3 and 4 (0-indexed: [2:4])
    result = app.get_items(page=2, per_page=2)
    assert result == ["item3", "item4"]
