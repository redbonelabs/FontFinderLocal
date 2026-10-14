"""Only cataloged, unchanged faces are exposed. Collections become standalone sfnt."""
from io import BytesIO
from pathlib import Path
from collections import OrderedDict
import threading
from fontTools.ttLib import TTFont
from .metadata import signature


class FontUnavailable(Exception):
    pass


def locate(face):
    for location in face["locations"]:
        path = Path(location["path"])
        try:
            if path.is_file() and signature(path) == location["signature"]:
                return path
        except OSError:
            continue
    raise FontUnavailable("Font file changed or is unavailable. Rescan fonts.")


class Renderer:
    def __init__(self, max_bytes=32 * 1024 * 1024):
        self.cache = OrderedDict()
        self.max_bytes = max_bytes
        self.size = 0
        self.lock = threading.Lock()

    def asset(self, face):
        with self.lock:
            path = locate(face)
            key = face["id"]
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            try:
                with path.open("rb") as file:
                    collection = file.read(4) == b"ttcf"
                font = TTFont(path, fontNumber=face["face_index"] if collection else -1,
                              recalcBBoxes=False, recalcTimestamp=False)
                try:
                    font.flavor = None
                    output = BytesIO()
                    font.save(output)
                    asset = output.getvalue()
                finally:
                    font.close()
            except Exception as exc:
                raise FontUnavailable("This face could not be prepared for browser rendering.") from exc
            if len(asset) <= self.max_bytes:
                while self.cache and self.size + len(asset) > self.max_bytes:
                    _, old = self.cache.popitem(last=False)
                    self.size -= len(old)
                self.cache[key] = asset
                self.size += len(asset)
            return asset
