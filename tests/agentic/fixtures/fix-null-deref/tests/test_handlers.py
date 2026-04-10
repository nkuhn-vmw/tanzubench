from app.handlers import greet

def test_happy_path():
    assert greet({"user": "alice"}) == "Hello, ALICE!"

def test_missing_user():
    # The fix should make this return a default, not crash.
    result = greet({})
    assert "guest" in result.lower() or "anonymous" in result.lower()
