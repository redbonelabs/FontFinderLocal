import hashlib
import os
from pathlib import Path
import re
import secrets
import subprocess
from typing import Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .config import Config, APP_ROOT
from .discovery import Catalog, validate_directory
from .persistence import Store
from .rendering import Renderer, FontUnavailable, locate

FONT_ID = re.compile(r"^[a-f0-9]{64}-\d{1,5}$")


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(default="SUPREME", max_length=10000)
    size: int = Field(default=64, ge=16, le=160)
    density: Literal["comfortable", "compact"] = "comfortable"
    sort: Literal["name", "style", "favorites"] = "name"
    query: str = Field(default="", max_length=500)
    style: Literal["all", "regular", "bold", "italic", "variable"] = "all"
    category: Literal["all", "serif", "sans-serif", "monospace", "script", "decorative", "symbol", "unknown"] = "all"
    source: Literal["all", "installed", "custom"] = "all"
    favorites_only: bool = False
    compare: list[str] = Field(default_factory=list, max_length=12)


class DirectoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=4096)
    recursive: bool = True


class FavoriteInput(BaseModel):
    enabled: bool


def create_app(config=None, *, scan_on_start=True, token=None, shutdown=None):
    config = config or Config.load()
    config.prepare()
    store, renderer = Store(config.data_dir), Renderer()
    catalog = Catalog(store)
    token = token or secrets.token_urlsafe(32)
    from .matching.service import MatchingService
    from .matching.routes import router as matching_router
    matching = MatchingService(config, catalog, renderer)

    @asynccontextmanager
    async def lifespan(app):
        matching.start_cleanup()
        if scan_on_start:
            catalog.start()
        yield
        matching.close()
        if catalog.worker:
            catalog.worker.join(timeout=10)

    app = FastAPI(title="FontFinderLocal", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.catalog = catalog
    app.state.store = store
    app.state.token = token
    app.state.matching = matching
    app.include_router(matching_router(matching))

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        # Host validation blocks DNS rebinding. No CORS is enabled.
        host = request.headers.get("host", "")
        if not re.fullmatch(r"127\.0\.0\.1(?::\d{1,5})?", host):
            return JSONResponse({"detail": "Use the application's 127.0.0.1 address."}, status_code=403)
        origin = request.headers.get("origin")
        if (origin and origin != f"http://{host}") or request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-origin requests are not allowed."}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            supplied = request.headers.get("x-fontfinder-token", "")
            if not secrets.compare_digest(supplied, token):
                return JSONResponse({"detail": "Session expired. Reload this page."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if not request.url.path.endswith("/asset"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        import logging
        logging.getLogger(__name__).exception("Request failed", exc_info=exc)
        return JSONResponse({"detail": "A local operation failed. See data/fontfinder.log and try again."}, status_code=500)

    def face_for(font_id):
        if not FONT_ID.fullmatch(font_id):
            raise HTTPException(404, "Unknown font identifier.")
        face = catalog.get(font_id)
        if not face:
            raise HTTPException(404, "Font is no longer in the catalog. Rescan fonts.")
        return face

    @app.get("/api/health")
    def health():
        return {"application": "FontFinderLocal", "version": "2.0.0"}

    @app.get("/api/bootstrap")
    def bootstrap():
        return {"token": token, "settings": Preferences(**store.get("settings", {})).model_dump(),
                "favorites": store.favorites(), "directories": store.get("directories", []),
                "can_open_folder": os.name == "nt"}

    @app.get("/api/fonts")
    def fonts():
        return catalog.snapshot()

    @app.get("/api/scan")
    def scan_status():
        with catalog.lock:
            return {"revision": catalog.revision, **catalog.status}

    @app.post("/api/rescan")
    def rescan():
        return {"started": catalog.start()}

    @app.get("/api/fonts/{font_id}")
    def details(font_id: str):
        return face_for(font_id)

    @app.get("/api/fonts/{font_id}/asset")
    def asset(font_id: str):
        face = face_for(font_id)
        try:
            data = renderer.asset(face)
        except FontUnavailable as exc:
            raise HTTPException(409, str(exc)) from exc
        return Response(data, media_type="font/otf" if face["format"] == "OpenType/CFF" else "font/ttf",
                        headers={"Cache-Control": "private, max-age=31536000, immutable", "ETag": f'"{font_id}"'})

    @app.put("/api/favorites/{font_id}")
    def favorite(font_id: str, body: FavoriteInput):
        face_for(font_id)
        store.favorite(font_id, body.enabled)
        return {"favorites": store.favorites()}

    @app.put("/api/settings")
    def settings(body: Preferences):
        if any(not FONT_ID.fullmatch(i) for i in body.compare):
            raise HTTPException(422, "Invalid comparison font identifier.")
        store.put("settings", body.model_dump())
        return body

    @app.post("/api/directories")
    def add_directory(body: DirectoryInput):
        try:
            path = validate_directory(body.path)
        except (ValueError, OSError) as exc:
            raise HTTPException(422, str(exc)) from exc
        with catalog.lock:
            if catalog.status["running"]:
                raise HTTPException(409, "Wait for the current scan to finish, then try again.")
            directories = store.get("directories", [])
            if any(os.path.normcase(d["path"]) == os.path.normcase(str(path)) for d in directories):
                raise HTTPException(409, "This folder is already configured.")
            directory = {"id": hashlib.sha256(os.path.normcase(str(path)).encode()).hexdigest()[:20],
                         "path": str(path), "recursive": body.recursive}
            directories.append(directory)
            store.put("directories", directories)
            catalog.start()
        return {"directories": directories}

    @app.delete("/api/directories/{directory_id}")
    def remove_directory(directory_id: str):
        with catalog.lock:
            if catalog.status["running"]:
                raise HTTPException(409, "Wait for the current scan to finish, then try again.")
            directories = store.get("directories", [])
            if not any(d["id"] == directory_id for d in directories):
                raise HTTPException(404, "Unknown custom folder.")
            directories = [d for d in directories if d["id"] != directory_id]
            store.put("directories", directories)
            catalog.start()
        return {"directories": directories}

    @app.post("/api/fonts/{font_id}/open-folder")
    def open_folder(font_id: str):
        face = face_for(font_id)
        if os.name != "nt":
            raise HTTPException(400, "Opening Explorer is available on Windows only.")
        try:
            path = locate(face)
            explorer = Path(os.environ.get("WINDIR", "C:/Windows")) / "explorer.exe"
            subprocess.Popen([str(explorer), "/select,", str(path)], shell=False)
        except (OSError, FontUnavailable) as exc:
            raise HTTPException(409, "The source folder is unavailable. Rescan fonts.") from exc
        return {"opened": True}

    @app.post("/api/shutdown")
    def stop():
        if shutdown is None:
            raise HTTPException(409, "Stop this server from its terminal.")
        shutdown()
        return {"stopping": True}

    @app.get("/")
    def index():
        return FileResponse(APP_ROOT / "frontend" / "index.html")

    app.mount("/static", StaticFiles(directory=APP_ROOT / "frontend"), name="static")
    return app
