import subprocess, sys

def test_cli_greets():
    r = subprocess.run([sys.executable, "cli.py", "alice"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "hello, alice" in r.stdout.lower()

def test_cli_exits_nonzero_on_missing_arg():
    r = subprocess.run([sys.executable, "cli.py"], capture_output=True, text=True)
    assert r.returncode != 0
