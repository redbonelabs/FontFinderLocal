"""Validated local uploads, bounded temporary storage, no user paths in endpoints."""
from io import BytesIO
from pathlib import Path
import secrets
import threading
import time
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD = 20 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_SIDE = 10000
WORK_SIDE = 2048
FORMATS = {"PNG", "JPEG", "BMP", "TIFF", "WEBP"}
TTL = 3600


class ImageError(ValueError):
    pass


def decode(data):
    if not data or len(data) > MAX_UPLOAD:
        raise ImageError("Choose an image smaller than 20 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as check:
                fmt, width, height = check.format, *check.size
                if fmt not in FORMATS:
                    raise ImageError("Supported image contents: PNG, JPEG, BMP, TIFF, or WebP.")
                if width * height > MAX_PIXELS or max(width, height) > MAX_SIDE or min(width, height) < 2:
                    raise ImageError("Image must be at most 20 megapixels and 10,000 pixels per side.")
                check.verify()
            with Image.open(BytesIO(data)) as opened:
                animated = getattr(opened, "n_frames", 1) > 1
                image = ImageOps.exif_transpose(opened).convert("RGBA")
        notes = ["Only the first frame/page is used."] if animated else []
        if max(image.size) > WORK_SIDE:
            image.thumbnail((WORK_SIDE, WORK_SIDE), Image.Resampling.LANCZOS)
            notes.append("Working preview downsampled to 2048 pixels on its longest side; original upload is retained temporarily.")
        return image, notes
    except ImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageError("This file is not a safe, readable supported image.") from exc


def png_bytes(image):
    output = BytesIO(); image.save(output, format="PNG"); return output.getvalue()


class ImageStore:
    def __init__(self, data_dir):
        self.root = data_dir / "matching-temp"
        self.root.mkdir(parents=True, exist_ok=True)
        self.items = {}
        self.lock = threading.RLock()
        self.cleanup()

    def cleanup(self):
        with self.lock:
            now = time.time()
            expired = [key for key, item in self.items.items() if now - item["touched"] > TTL]
            for key in expired:
                self.remove(key)
            # Only our generated files; ignore other extensions and never follow directory trees.
            for file in self.root.glob("*.upload"):
                if now - file.stat().st_mtime > TTL:
                    file.unlink(missing_ok=True)
                    file.with_suffix(".png").unlink(missing_ok=True)

    def add(self, data):
        image, notes = decode(data)
        with self.lock:
            self.cleanup()
            if len(self.items) >= 6:
                self.remove(min(self.items, key=lambda key: self.items[key]["touched"]))
            key = secrets.token_hex(16)
            (self.root / f"{key}.upload").write_bytes(data)
            image.save(self.root / f"{key}.png")
            item = {"id": key, "width": image.width, "height": image.height, "notes": notes, "touched": time.time()}
            self.items[key] = item
            return {k: v for k, v in item.items() if k != "touched"}

    def get(self, key):
        with self.lock:
            self.cleanup()
            if key not in self.items:
                raise ImageError("Image expired or was removed. Upload it again.")
            self.items[key]["touched"] = time.time()
            with Image.open(self.root / f"{key}.png") as image:
                return image.copy()

    def remove(self, key):
        with self.lock:
            if key not in self.items:
                return
            self.items.pop(key)
            (self.root / f"{key}.upload").unlink(missing_ok=True)
            (self.root / f"{key}.png").unlink(missing_ok=True)
