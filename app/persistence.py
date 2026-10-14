"""SQLite stores metadata only; original font files are never copied."""
import json
import sqlite3
from contextlib import contextmanager


class Store:
    def __init__(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "fontfinder.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY, signature TEXT NOT NULL,
                    digest TEXT NOT NULL, metadata TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS favorites (id TEXT PRIMARY KEY);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key, default):
        with self.connect() as db:
            row = db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, json.dumps(value)))

    def cached(self, path, signature):
        with self.connect() as db:
            row = db.execute("SELECT digest, metadata FROM files WHERE path=? AND signature=?",
                             (str(path), signature)).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def cache(self, path, signature, digest, metadata):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?)",
                       (str(path), signature, digest, json.dumps(metadata)))

    def prune(self, paths):
        with self.connect() as db:
            current = {r[0] for r in db.execute("SELECT path FROM files")}
            db.executemany("DELETE FROM files WHERE path=?", [(p,) for p in current - set(paths)])

    def favorites(self):
        with self.connect() as db:
            return [r[0] for r in db.execute("SELECT id FROM favorites")]

    def favorite(self, font_id, enabled):
        with self.connect() as db:
            if enabled:
                db.execute("INSERT OR IGNORE INTO favorites VALUES (?)", (font_id,))
            else:
                db.execute("DELETE FROM favorites WHERE id=?", (font_id,))
