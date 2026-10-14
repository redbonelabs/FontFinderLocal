# Step 1 validation

Validated on Windows on October 14, 2026.

## Environment and result

- Final project environment: **Python 3.13.16**, FastAPI 0.143.1, Uvicorn 0.54.0, fontTools 4.67.0. Tested versions are recorded in `requirements-lock.txt`.
- **23 automated tests passed** on Python 3.13 in 14.81 seconds. Earlier component tests and the process lifecycle test also passed on Python 3.12.14.
- `pip check`: no broken requirements. Python compilation and Node JavaScript syntax checks passed. The frontend uses native ES modules; no frontend build or Node runtime is required.
- One upstream Starlette warning reports that its httpx TestClient integration is deprecated in favor of httpx2. It does not affect test results or the runtime application.

## Actual local runtime

The app was started through `app.startup`, bound to `127.0.0.1:8766`, and checked through live HTTP requests. This machine provided **1,117 font files**, yielding **639 distinct faces in 398 families** after duplicate merging. The scan reported no unreadable/corrupt file errors. Restart loaded metadata for all 1,117 files from cache.

`tests/runtime_check.py` fetched health, HTML, catalog, details, and real font assets. Served data was reparsed with fontTools to verify valid output:

| Input | Example | Verified output |
|---|---|---|
| TTF | 8Pin Matrix | Standalone TrueType asset |
| OTF/CFF | AkzidenzGroteskBQ-Cnd | Valid OpenType/CFF asset |
| Variable | Bahnschrift | Variation tables retained |
| TTC | Cambria | Standalone face rather than a collection |

Run again with the app running:

```powershell
.\.venv\Scripts\python.exe -m tests.runtime_check
```

The machine-specific report is written to ignored `test-results/runtime-api.json`.

## Browser smoke checks

Used the Codex in-app browser against the real Windows server:

- Confirmed dynamically registered face aliases, completed `FontFace` loading, and visible previews from actual local font assets.
- Entered `  Hello, WORLD!  ` and inspected DOM text to confirm both leading/trailing spaces and punctuation survived exactly.
- Searched Arial; combined bold and sans-serif filters produced 57 faces; style sorting and density toggles worked.
- Favorited a face, selected two faces for comparison, removed one independently, and opened details from comparison.
- Reloaded the page and restarted the server; preferences and the favorite survived. Comparison IDs persisted.
- Added an uninstalled synthetic font through Settings, filtered to custom fonts, confirmed its asset loaded, then removed the folder registration. Original files remained intact.
- Opened Bahnschrift details and selected Bold Condensed; both library and dialog previews used `wght=700` and `wdth=75`.
- Changed size from 64 to 65 px and checked the rendered sample styles.
- Scrolled to the end of all 639 faces; only four cards were mounted at that viewport size. Yu Gothic UI collection faces completed browser loading.
- Inspected desktop and 390 px wide layouts. No document-level horizontal overflow was present at the narrow viewport; wide samples scroll inside cards.
- Confirmed a browser-rejected legacy font displays a visible rendering error instead of silently displaying fallback text. Successful metadata discovery alone is not a guarantee of browser compatibility.
- Cleared test favorites, comparisons, and custom-folder registrations and restored SUPREME / 64 px / default filters before handoff.

## Process and security checks

The automated lifecycle test starts separate real processes with an occupied preferred port, verifies fallback to another loopback port, runs a duplicate launch, saves settings, shuts down via the authenticated stop command, restarts, checks persisted text and a fresh session token, and shuts down again. A Windows lock-file read issue found during live testing was fixed and covered by a regression test.

API tests reject foreign hosts/origins, missing/invalid mutation tokens, unknown IDs, encoded filesystem paths, and static traversal. They validate settings and directories and confirm that the Explorer command resolves the catalog ID rather than accepting an arbitrary path. Explorer process invocation is mocked in automated tests; a visible Explorer window was not part of the browser smoke test. Clipboard permission behavior and default-browser auto-opening were not tested across browser/Windows configurations.

## Scope limits

Image matching and executable packaging were deliberately not implemented. No GitHub repository was initialized or published. Browser checks cover the in-app browser on this machine, not a full Edge/Chrome/Firefox compatibility matrix, every installed font, or a synthetic many-thousand-face performance benchmark. Variable metadata is unit-tested with generated fixtures and actual variation rendering is checked with Bahnschrift.
