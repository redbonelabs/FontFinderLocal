"""Process lock, pre-bound loopback socket, browser launch, and graceful stop."""
import argparse
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
from urllib.request import Request, urlopen
import webbrowser

from .config import Config


class InstanceLock:
    def __init__(self, path):
        self.file = open(path, "a+b")
        # Reading the locked byte fails on Windows when another process owns it.
        if os.fstat(self.file.fileno()).st_size == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        self.acquired = False

    def acquire(self):
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.acquired = True
            return True
        except OSError:
            return False

    def close(self):
        if self.acquired:
            self.file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()


def bind_socket(port=8766):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name == "nt":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    return sock


def running_instance(path):
    try:
        state = json.loads(path.read_text())
        port = int(state["port"])
        if not 1 <= port <= 65535:
            return None
        url = f"http://127.0.0.1:{port}"
        with urlopen(url + "/api/bootstrap", timeout=1) as response:
            if json.load(response)["token"] != state["token"]:
                return None
        return {**state, "url": url}
    except (OSError, ValueError, KeyError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="FontFinderLocal — local font browser")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args(argv)
    config = Config(Config.load().data_dir, port=args.port)
    config.prepare()
    state_path = config.data_dir / "server.json"
    if args.stop:
        state = running_instance(state_path)
        if not state:
            print("FontFinderLocal is not running.")
            return 0
        request = Request(state["url"] + "/api/shutdown", data=b"{}", method="POST",
                          headers={"X-FontFinder-Token": state["token"], "Content-Type": "application/json"})
        with urlopen(request, timeout=5):
            pass
        print("Shutdown requested.")
        return 0
    lock = InstanceLock(config.data_dir / "instance.lock")
    if not lock.acquire():
        try:
            for _ in range(40):
                state = running_instance(state_path)
                if state:
                    print("FontFinderLocal is already running at " + state["url"])
                    if not args.no_browser:
                        webbrowser.open(state["url"])
                    return 0
                time.sleep(0.25)
            print("Another instance is starting or stopping. Try again shortly.")
            return 1
        finally:
            lock.close()
    sock = None
    try:
        handler = RotatingFileHandler(config.data_dir / "fontfinder.log", maxBytes=2_000_000, backupCount=2, encoding="utf-8")
        logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(asctime)s %(levelname)s %(name)s %(message)s")
        import uvicorn
        from .api import create_app
        token = secrets.token_urlsafe(32)
        sock = bind_socket(config.port)
        port = sock.getsockname()[1]
        app = create_app(config, token=token, shutdown=lambda: setattr(server, "should_exit", True))
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, access_log=False))
        temp = state_path.with_suffix(".tmp")
        temp.write_text(json.dumps({"port": port, "token": token, "pid": os.getpid()}))
        temp.replace(state_path)
        url = f"http://127.0.0.1:{port}"
        print(f"\nFontFinderLocal: {url}\nPress Ctrl+C here, or run Stop-FontFinderLocal.bat to stop.\n", flush=True)
        if not args.no_browser:
            def open_when_ready():
                for _ in range(100):
                    if server.started:
                        webbrowser.open(url)
                        return
                    if server.should_exit:
                        return
                    time.sleep(0.1)
            threading.Thread(target=open_when_ready, daemon=True).start()
        server.run(sockets=[sock])
        return 0
    finally:
        state_path.unlink(missing_ok=True)
        if sock:
            sock.close()
        lock.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"FontFinderLocal could not start: {exc}", file=sys.stderr)
        sys.exit(1)
