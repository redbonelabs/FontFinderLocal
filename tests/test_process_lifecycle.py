"""Exercise real OS locks and launcher behavior across independent processes."""
import json
import os
import subprocess
import sys
import time
from urllib.request import Request, urlopen

from app.config import APP_ROOT
from app.startup import bind_socket


def test_real_launch_duplicate_fallback_persistence_and_shutdown(tmp_path):
    directory = tmp_path / "runtime-data"
    env = {**os.environ, "FONTFINDER_DATA_DIR": str(directory)}
    busy = bind_socket(0)
    preferred = busy.getsockname()[1]
    command = [sys.executable, "-m", "app.startup", "--no-browser", "--port", str(preferred)]
    process = None

    def request(state, path, body=None):
        url = f"http://127.0.0.1:{state['port']}" + path
        req = Request(url, data=None if body is None else json.dumps(body).encode(),
                      headers={"X-FontFinder-Token": state["token"], "Content-Type": "application/json"},
                      method="PUT" if body is not None else "GET")
        with urlopen(req, timeout=3) as response:
            return json.load(response)

    def ready():
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            assert process.poll() is None, "Launcher exited unexpectedly"
            try:
                state = json.loads((directory / "server.json").read_text())
                if request(state, "/api/health")["application"] == "FontFinderLocal": return state
            except (OSError, ValueError): pass
            time.sleep(.1)
        raise AssertionError("Server did not become ready")

    def stop():
        result = subprocess.run([sys.executable, "-m", "app.startup", "--stop"], cwd=APP_ROOT, env=env,
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        process.wait(timeout=30)
        assert process.returncode == 0
        assert not (directory / "server.json").exists()

    try:
        process = subprocess.Popen(command, cwd=APP_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        first = ready(); assert first["port"] != preferred
        duplicate = subprocess.run(command, cwd=APP_ROOT, env=env, capture_output=True, text=True, timeout=15)
        assert duplicate.returncode == 0 and "already running" in duplicate.stdout
        assert json.loads((directory / "server.json").read_text())["pid"] == first["pid"]
        settings = request(first, "/api/bootstrap")["settings"]
        settings["text"] = '  Restart, SAME text!  '
        request(first, "/api/settings", settings)
        stop()
        process = subprocess.Popen(command, cwd=APP_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        second = ready()
        assert first["token"] != second["token"]
        assert request(second, "/api/bootstrap")["settings"]["text"] == settings["text"]
        stop()
    finally:
        busy.close()
        if (directory / "server.json").exists():
            subprocess.run([sys.executable, "-m", "app.startup", "--stop"], cwd=APP_ROOT, env=env,
                           capture_output=True, timeout=15)
        if process is not None and process.poll() is None:
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate(); process.wait(timeout=10)
