from app import get_response


def test_format():
    assert get_response()["data"] == 42
