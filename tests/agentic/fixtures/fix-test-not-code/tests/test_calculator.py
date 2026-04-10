from calculator import add, sub, mul, div


def test_add():
    assert add(2, 3) == 5


def test_sub():
    assert sub(10, 4) == 6


def test_mul():
    assert mul(3, 4) == 12


def test_div():
    assert div(10, 3) == 3  # BUG: wrong expected value, should be ~3.333...
