"""Real WSGI HTTP smoke test, without publishing or using local collections."""
import importlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest


@pytest.mark.parametrize("port", ["", "0", "65536", "abc", "12.5"])
def test_runner_rejects_bad_port_before_starting(port):
    module = importlib.import_module("serve_hosted")
    with pytest.raises(ValueError):
        module.validate_port(port)


def test_real_production_server_http_and_quiet_logs(tmp_path):
    importlib.import_module("serve_hosted")  # Expected feature failure before implementation.
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    storage = tmp_path / "durable"
    storage.mkdir()
    environment = dict(os.environ, TRIPPLANNER_SECRET_KEY="c5" * 32,
                       TRIPPLANNER_STORAGE_DIR=str(storage), TRIPPLANNER_PUBLIC_HOST="planner.example",
                       PORT=str(port), PYTHONUTF8="1")
    log_path = tmp_path / "server.log"
    with log_path.open("wb") as log:
        process = subprocess.Popen([sys.executable, str(root / "serve_hosted.py")],
                                   cwd=root, env=environment, stdout=log, stderr=log,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            deadline = time.monotonic() + 12
            while True:
                try:
                    with urlopen(Request(f"http://127.0.0.1:{port}/healthz", headers={"Host": "planner.example"}), timeout=1) as response:
                        assert response.status == 200
                        assert b'"ok"' in response.read()
                        break
                except (URLError, TimeoutError):
                    assert process.poll() is None, "Production runner stopped before readiness."
                    assert time.monotonic() < deadline, "Production runner did not become ready."
                    time.sleep(0.05)
            with urlopen(Request(f"http://127.0.0.1:{port}/plan?private-test-marker=hidden", headers={"Host": "planner.example"}), timeout=3) as response:
                assert response.status == 200
                assert response.headers["Cache-Control"] == "private, no-store"
                assert "Secure" in response.headers.get("Set-Cookie", "")
                assert b"TripPlanner" in response.read()
            with pytest.raises(HTTPError) as error:
                urlopen(Request(f"http://127.0.0.1:{port}/", headers={"Host": "attacker.example"}), timeout=3)
            assert error.value.code == 400
        finally:
            process.terminate()
            process.wait(timeout=8)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    assert "private-test-marker" not in text and environment["TRIPPLANNER_SECRET_KEY"] not in text
    assert "Development Server" not in text and "Traceback" not in text
