"""Native Windows discovery plus explicit directory scans and incremental caching."""
import hashlib
import os
from pathlib import Path
import threading
import logging

from .metadata import SUPPORTED, extract_metadata, signature

log = logging.getLogger(__name__)


def validate_directory(raw):
    if not isinstance(raw, str) or not raw.strip() or "\x00" in raw:
        raise ValueError("Enter a folder path.")
    expanded = os.path.expandvars(raw.strip().strip('"'))
    # Network shares are outside this local-only application's scope.
    if expanded.startswith(("\\\\", "//")):
        raise ValueError("Choose a local folder, not a network share.")
    path = Path(expanded).expanduser()
    if not path.is_absolute():
        raise ValueError("Enter an absolute folder path.")
    try:
        path = path.resolve(strict=True)
        if not path.is_dir():
            raise ValueError("The path must be a folder.")
        with os.scandir(path):
            pass
    except OSError as exc:
        raise ValueError("The folder does not exist or cannot be read.") from exc
    if str(path).startswith(("\\\\", "//")):
        raise ValueError("Choose a local folder, not a network share.")
    return path


def walk_fonts(directory, recursive, issue):
    try:
        for root, dirs, files in os.walk(directory, followlinks=False, onerror=lambda e: issue(str(e.filename), "Folder cannot be read.")):
            # Junctions and symlinks can escape a configured directory or create loops.
            dirs[:] = [d for d in dirs if not Path(root, d).is_symlink()
                       and not (hasattr(Path(root, d), "is_junction") and Path(root, d).is_junction())]
            for filename in files:
                path = Path(root, filename)
                if path.suffix.lower() in SUPPORTED and not path.is_symlink():
                    yield path
            if not recursive:
                break
    except OSError:
        issue(str(directory), "Folder cannot be read.")


def system_sources(issue):
    if os.name != "nt":
        # Useful for development; Windows native discovery remains the primary path.
        for directory in (Path("/usr/share/fonts"), Path.home() / ".local/share/fonts", Path("/Library/Fonts")):
            if directory.is_dir():
                yield from walk_fonts(directory, True, issue)
        return
    import winreg
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    user_fonts = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "Microsoft/Windows/Fonts"
    for directory in (windows_fonts, user_fonts):
        if directory.is_dir():
            yield from walk_fonts(directory, True, issue)
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_READ | view) as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        _, value, _ = winreg.EnumValue(key, i)
                        if isinstance(value, str):
                            path = Path(os.path.expandvars(value))
                            if not path.is_absolute():
                                path = (user_fonts / path) if hive == winreg.HKEY_CURRENT_USER and (user_fonts / path).is_file() else windows_fonts / path
                            if path.suffix.lower() in SUPPORTED:
                                yield path
            except FileNotFoundError:
                pass
            except OSError:
                issue("Windows font registry", "Some registry entries could not be read.")


class Catalog:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.faces = {}
        self.revision = 0
        self.status = {"running": False, "processed": 0, "total": 0, "issues": [], "cached": 0}
        self.worker = None

    def snapshot(self):
        with self.lock:
            return {"fonts": list(self.faces.values()), "revision": self.revision,
                    "scan": {**self.status, "issues": list(self.status["issues"])}}

    def get(self, font_id):
        with self.lock:
            return self.faces.get(font_id)

    def start(self):
        with self.lock:
            if self.status["running"]:
                return False
            self.status = {"running": True, "processed": 0, "total": 0, "issues": [], "cached": 0}
            self.worker = threading.Thread(target=self._scan, name="font-discovery", daemon=True)
            self.worker.start()
            return True

    def issue(self, path, message):
        with self.lock:
            if len(self.status["issues"]) < 500:
                self.status["issues"].append({"path": path, "message": message})

    def _scan(self):
        faces, candidates = {}, {}
        try:
            def add(path, source):
                try:
                    path = path.resolve()
                    key = os.path.normcase(str(path))
                    candidates.setdefault(key, {"path": path, "sources": set()})["sources"].add(source)
                except OSError:
                    self.issue(str(path), "Font path cannot be resolved.")
            for path in system_sources(self.issue):
                add(path, "installed")
            for directory in self.store.get("directories", []):
                if not Path(directory["path"]).is_dir():
                    self.issue(directory["path"], "Configured folder is unavailable.")
                    continue
                for path in walk_fonts(directory["path"], directory["recursive"], self.issue):
                    add(path, "custom")
            with self.lock:
                self.status["total"] = len(candidates)
            for candidate in candidates.values():
                path, sources = candidate["path"], candidate["sources"]
                try:
                    sig = signature(path)
                    cached = self.store.cached(path, sig)
                    if cached:
                        digest, metadata = cached
                        with self.lock:
                            self.status["cached"] += 1
                    else:
                        with path.open("rb") as file:
                            digest = hashlib.file_digest(file, "sha256").hexdigest()
                        metadata = extract_metadata(path)
                        if signature(path) != sig:
                            raise ValueError("Font changed during scan")
                        self.store.cache(path, sig, digest, metadata)
                    for face in metadata:
                        font_id = f"{digest}-{face['face_index']}"
                        location = {"path": str(path), "signature": sig, "sources": sorted(sources)}
                        if font_id in faces:
                            faces[font_id]["locations"].append(location)
                            faces[font_id]["sources"] = sorted(set(faces[font_id]["sources"]) | sources)
                        else:
                            faces[font_id] = {**face, "id": font_id, "sources": sorted(sources),
                                              "path": str(path), "locations": [location]}
                except Exception:
                    log.info("Unable to parse font %s", path, exc_info=True)
                    self.issue(str(path), "Font is unreadable, unsupported, or corrupt.")
                with self.lock:
                    self.status["processed"] += 1
            self.store.prune(str(c["path"]) for c in candidates.values())
            with self.lock:
                self.faces = faces
                self.revision += 1
        except Exception:
            log.exception("Font scan failed")
            self.issue("Font discovery", "Scan could not finish. See the local log and retry.")
        finally:
            with self.lock:
                self.status["running"] = False
