from dataclasses import dataclass
from pathlib import Path
import os
import sys


APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


@dataclass(frozen=True)
class Config:
    data_dir: Path
    host: str = "127.0.0.1"
    port: int = 8766

    def __post_init__(self):
        if self.host != "127.0.0.1":
            raise ValueError("FontFinderLocal only supports 127.0.0.1")
        if not 0 <= self.port <= 65535:
            raise ValueError("Invalid port")

    @classmethod
    def load(cls):
        base = Path(sys.executable).parent if getattr(sys, "frozen", False) else APP_ROOT
        return cls(Path(os.environ.get("FONTFINDER_DATA_DIR", base / "data")).resolve())

    def prepare(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
