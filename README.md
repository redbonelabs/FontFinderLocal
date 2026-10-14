# FontFinderLocal

A Windows-first, fully local font browser. Type a phrase and preview the actual font faces on your computer, including fonts in folders that are not installed in Windows. Normal operation requires no internet, cloud account, Node.js, or AI software.

## Features

- Dark interface with immediate text previews (default: **SUPREME**), 16–160 px size, and comfortable/compact density.
- Search family, full name, and style; filter bold, italic, regular, variable, declared category, source, and favorites. Sort by name, style, or favorites.
- Persistent favorites and a comparison workspace for up to 12 independent faces.
- Details with Unicode metadata, full paths, collection indices, clipboard actions, and a catalog-validated Windows Explorer action.
- Variable axes and named instances in details; adjustments apply to previews for the current session.
- Machine and per-user font directories, both Windows registry views, and recursive or shallow custom folders.
- TTF, OTF, TTC/OTC, WOFF, and WOFF2 input. Collection faces and compressed formats are served as standalone OpenType/TrueType assets.
- Metadata caching in SQLite, content-based file deduplication, background rescans, and explicit discovery/rendering errors.
- Virtualized result list, four concurrent asset loads, bounded browser font registration and a 32 MiB server asset cache.
- No font files are uploaded, modified, installed, or copied into the application data directory.

Image Font Finder is visibly marked **Coming soon**. Image matching is not implemented in this milestone.

## Requirements and first-time setup

For source-based use, install **Python 3.13** (64-bit recommended) with the Windows `py` launcher, and use a current Edge, Chrome, or Firefox browser. The code also runs on Python 3.12. Internet is needed only for initial dependency installation. Administrator privileges are not required by this app.

1. Put this project in a writable local folder.
2. Double-click **Setup-FontFinderLocal.bat**. It creates `.venv` with Python 3.13 and installs the tested versions in `requirements-lock.txt`. An existing project virtual environment is reused. `requirements.txt` describes the supported top-level dependency ranges for development updates.
3. Double-click **Start-FontFinderLocal.bat**.

Alternatively, in PowerShell from the project folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\Start-FontFinderLocal.bat
```

The launch script always uses the project's virtual environment. It prefers `http://127.0.0.1:8766`, automatically selects an available port if necessary, prints the actual address, and opens your default browser when ready. A repeated launch reopens the existing instance instead of starting another server.

For development without opening a browser:

```powershell
.\.venv\Scripts\python.exe -m app.startup --no-browser
```

This development checkout is already provisioned with a project-local Python 3.13 runtime in `.python/` and a ready `.venv`; no manual setup is needed on this machine. Keep `.python/` while using that virtual environment. Setup can reuse this local runtime if `.venv` needs rebuilding. Neither directory is a packaged application distribution or tracked source.

## Shutdown

Press **Ctrl+C in the startup terminal**, or double-click **Stop-FontFinderLocal.bat**. Closing a browser tab does not stop the server. The stop script contacts the authenticated local shutdown endpoint; it does not kill unrelated Python processes. Windows releases the process lock after a crash, so a subsequent launch can recover.

## Using the library

Enter text in the large preview field; spaces, line breaks, capitalization, and punctuation are preserved. Long or multiline samples scroll within their cards. The star saves a favorite; `+` selects a face for comparison. Open the **Compare** tab to view selected faces with the same text and size, remove them individually, or open details. Filtering the library does not remove comparison selections.

Click a font name or its information button to open details. Variable fonts expose sliders and named instances when declared in the file. Axis adjustments reset when the page reloads. Escape closes the details dialog.

Use **Rescan fonts** after installing, changing, or moving fonts. Unchanged files reuse cached metadata. The previous catalog remains available while a new scan runs and is replaced atomically when complete. Discovery issues appear in Settings; a damaged file does not prevent other files from loading.

### Custom folders

In **Settings**, paste an absolute local folder path, choose whether to include subfolders, and click **Add folder**. A scan starts automatically. **Remove** unregisters the folder and rescans without deleting anything. To change recursive scanning, remove and re-add the folder with the desired option. Directory changes wait until a running scan finishes. UNC network paths are not accepted, and nested directory links/junctions are not traversed.

## Local data and portability

`data/` holds `fontfinder.sqlite3`, a rotating log, and transient process state. It is separate from source and excluded from version control. Font binaries are read from their original locations, and generated browser assets stay in bounded memory/browser cache. To reset the app, stop it and rename `data/`; a new directory will be created on launch.

`FONTFINDER_DATA_DIR` can override the data location, for example:

```powershell
$env:FONTFINDER_DATA_DIR = Join-Path $PWD 'portable-data'
.\Start-FontFinderLocal.bat
```

Use the same environment override when stopping the app. The single-instance lock applies per data directory. Multiple separate copies with different data directories may run independently.

Future frozen builds use resources relative to the bundle and default to a data folder beside the executable. This milestone does **not** include an executable distribution. Virtual environments are machine-specific: after moving the source project to another computer, recreate `.venv` with the setup script. Windows fonts are never part of the distribution.

## Security

The launcher binds only to `127.0.0.1`. Host and Origin checks block foreign hosts and cross-origin requests; mutations require a per-process token obtained by the local page. No permissive CORS configuration or CDN dependencies are used. Font assets and Explorer operations accept only catalog font IDs, never execution paths. Changed or missing font assets require a rescan. Font names and paths are rendered as text, not HTML. This protects against browser-origin attacks, not other software already running under your Windows account.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=test-results/pytest
```

Tests generate their own tiny font fixtures. They cover Unicode metadata, collections, variable metadata, compressed fonts, duplicate handling, cache reuse, directory validation, persistence, API security, controlled Explorer invocation, process locks, and port fallback. They do not redistribute Windows fonts. See `docs/VALIDATION.md` for the checks performed in this development session.

## Known limitations

- Browser support determines whether legacy, color, bitmap, or unusual OpenType fonts render. Unsupported assets show a visible error. Legacy `.fon` and `.fnt` files are not supported.
- Missing Unicode characters are explicitly warned about; the browser may use fallback for those characters. Coverage cannot prove that all shaping, color, or variation-selector behavior is correct.
- Categories use declared OS/2 family classification and fixed-pitch metadata. Unknown classification stays **Unclassified**; no visual categories are guessed.
- Exact duplicate **files** merge into one face per collection index, with all locations retained. Distinct binaries with identical names stay separate. A collection and a standalone export of one of its faces may appear separately.
- New/changed fonts require an explicit rescan; there is no filesystem watcher yet. Initial parsing time depends on library size. Very large/malformed fonts can be slow; parsing is isolated from HTTP handling in a background thread, not a sandboxed worker process.
- Comparison is limited to 12 faces. Large libraries use a virtual list, so browser Find searches only mounted cards; use the app's search field.
- Copy actions require browser clipboard permission. Explorer integration is Windows-only. The app's terminal must remain open unless it was deliberately started in the background.

## Troubleshooting

- **No Python / setup fails:** install Python 3.13 with its launcher, then run Setup again. The startup script reports missing dependencies clearly.
- **Port 8766 is busy:** read the actual address in the startup window. The app automatically chooses another port.
- **No fonts / missing custom fonts:** check Settings for unavailable paths and discovery issues, verify folder access, then rescan.
- **Font changed / preview failed:** rescan and retry. A genuinely incompatible face will continue to display a rendering error.
- **Preferences could not save:** verify write access and free space in the data directory. Check `data/fontfinder.log`.
- **Connection interrupted:** relaunch the app and open its printed address. After a restart, reload the page to obtain the new session token.
- **Startup fails:** inspect the terminal error and `data/fontfinder.log`; run Setup again if dependencies are missing. Do not launch Uvicorn on a public interface.
