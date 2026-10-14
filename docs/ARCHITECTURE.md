# Architecture

## Components

- `app/startup.py`: OS-held process lock, pre-bound loopback socket, ready-state browser opening, state file, authenticated shutdown, rotating logging.
- `app/config.py`: portable resource roots, writable data location, loopback-only configuration.
- `app/discovery.py`: Windows registry/directory enumeration, configured folder validation, background scanning, immutable catalog replacement, file-level SHA-256 identity and duplicate locations.
- `app/metadata.py`: fontTools Unicode name decoding, collection indices, axes/instances, declared categories, Unicode coverage. Independent of HTTP and the frontend.
- `app/rendering.py`: catalog-backed path lookup, freshness checks, collection/WOFF conversion to standalone sfnt, bounded in-memory asset cache.
- `app/persistence.py`: short-lived SQLite connections, WAL, metadata cache, favorites, preferences, configured folders.
- `app/api.py`: typed routes and validation, host/origin/token protections, static resources, controlled Explorer operation.
- `frontend/app.js`: view state, filtering, sorting, virtualized rows, comparisons, settings, accessible details dialog.
- `frontend/fonts.js`: unique FontFace aliases, readiness/error handling, Unicode coverage warnings, concurrency limit and registration eviction.
- `frontend/styles.css` / `index.html`: responsive dark interface, no build step or external runtime assets.
- `tests/`: generated font fixtures and behavior/security tests.

## Data flow

Startup acquires a per-data-directory process lock and binds a socket before Uvicorn starts, avoiding port-selection races. SQLite initializes before the background catalog scan. The API remains responsive during parsing. The frontend obtains saved state and a session token, polls scan progress, then retrieves the catalog only when its revision changes.

Discovery deduplicates paths, consults the metadata cache using schema version, size, mtime, and ctime, then hashes and parses changed files. Font IDs are `<SHA-256 of file>-<collection face index>`: renaming an unchanged file preserves its identity, and changing a file creates a new identity. Duplicate binaries share one entry with multiple locations/sources. Favorites referencing absent fonts remain stored, allowing restoration if the same file returns. Comparison IDs are retained, but unavailable faces are not shown.

The browser filters metadata locally and mounts only the viewport plus two overscan rows at either end. Each card registers the cataloged asset under a collision-free family alias. Four concurrent load requests and an 80-entry target limit bound active browser registration; mounted faces remain registered. Asset failure hides the sample instead of displaying a misleading fallback preview. Unicode coverage warns about individual missing characters.

The renderer converts fonts only when requested and preserves supported variation tables. Assets are capped to a 32 MiB LRU cache; larger assets are returned without retaining them. Browser HTTP caching uses content identity. No derivative font binary is persisted by the server.

All mutations require the process token and compatible Origin/Host headers. A font detail response may contain source paths, but paths are never trusted back from the browser to open or serve files. Font Explorer requests resolve the ID in the catalog and verify its file signature.

## Image Font Finder integration

Step 2 now implements this boundary in `app/matching/` and additive frontend modules. See `MATCHING_ARCHITECTURE.md` for the current implementation. The original design notes below describe the separation retained by that implementation.

Keep discovery, metadata, identity, and rendering as the shared foundation. Add image ingestion/preprocessing, a native rasterizer adapter, matching/indexing services, job progress/cancellation, and dedicated `/api/matching` routes. The matching service should consume catalog IDs and explicit variation coordinates. It should not implement a second scanner or depend on browser CSS names. Derived descriptors can use separate versioned SQLite tables keyed by font ID, rasterizer version, and preprocessing parameters.

The current browser asset renderer is not a pixel-analysis engine. Introduce native glyph rasterization as an additional adapter rather than overloading HTTP asset conversion. Expensive future matching jobs should run in bounded workers with cancellation and memory limits. Any executable packaging should bundle the frontend and Python dependencies while excluding `.venv`, local data, custom fonts, and system font binaries.
