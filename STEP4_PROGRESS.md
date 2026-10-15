# Step 4 portable Windows packaging

## Status: complete on the available Windows x64 host

Built and validated the actual portable distribution from protected application checkpoint `f46ca13`. Application source, frontend, matching algorithms and runtime requirements remain unchanged. Step 3 benchmark artifacts were preserved; no OCR or remote/GitHub work was performed.

## Deliverables

- EXE: `dist/FontFinderLocal/FontFinderLocal.exe` (keep its complete folder).
- ZIP: `releases/FontFinderLocal-Windows-x64-portable.zip`.
- ZIP size: 80,799,375 bytes (77.06 MiB).
- Unpacked size: 201,257,547 bytes (191.93 MiB).
- SHA-256: `aea558100924cae11dc315ee278b99cbbbb19bda9c6a9119c7c27df1c1460297`.
- Checksum and machine-readable build summary accompany the ZIP.

The package contains the frontend, embedded Python and native dependencies, Start/Stop batch launchers, instructions, build inventory and third-party license notices. It contains no user database, uploaded images or font files. Settings and caches are created in `data` beside the executable. The build script refuses to rebuild over runtime data before invoking PyInstaller.

## Completed validation

Extracted the final ZIP outside the repository to a path containing spaces and a non-ASCII character. Started from an unrelated working directory with PATH limited to Windows System32 and Python/venv/application environment overrides removed.

- Verified AMD64 executable and ZIP integrity.
- Independent startup, occupied-port fallback and second-launch instance reuse passed.
- All served frontend files matched protected source byte-for-byte.
- Discovered 642 installed font faces without scan issues; served TTF, CFF, TTC and variable font assets.
- Discovered and served three external custom-folder TTF/WOFF/WOFF2 fixtures.
- Native image processing and exact-text matching passed: 645 catalog faces, 617 eligible, 6.312 seconds for the API fixture. Excluded 27 missing-glyph faces and one unrenderable face without interrupting the search.
- Candidate previews, all four comparison modes, adjusted alignment, auto-align and cancellation passed.
- Inspected 79 loaded native modules: none came from the development tree; embedded Python loaded from the external package.
- Settings (including multiline text), favorites and custom folders survived restart.
- Both EXE --stop and authenticated shutdown exited cleanly and removed live server state.
- Browser validation against the external executable displayed all three custom previews with equal client/scroll heights (96 px), uploaded an image, accepted exact manual text PINBALL, completed all 645 faces in 5.5 seconds, ranked Arial Bold first, and displayed its loaded 620 x 146 overlay image. Screenshot inspected. Final browser-test process also stopped cleanly.

Regression tests: **43 pytest tests passed** in 15.52 seconds (one existing Starlette/httpx deprecation warning); **1 Node preview-row test passed**. Protected app/frontend diff against `f46ca13` is empty.

Detailed local evidence: `test-results/step4-portable-validation.json`, `test-results/step4-validation.log`, `test-results/step4-build.log`, and `releases/build-summary.json`. External test artifacts remain in `%TEMP%/FontFinderLocal-Step4-1jd_xhle`; test processes are stopped. The development server was not modified.

## Limitations and next action

No packaging blocker remains on this host. The executable is unsigned. A clean Windows VM or second physical machine was not available, so cross-machine compatibility and SmartScreen behavior remain unverified. Existing font coverage/renderability limitations remain unchanged. The next useful release check is extracting the ZIP on another Windows x64 machine without Python installed.

To launch, extract the entire ZIP into a writable local folder and double-click Start-FontFinderLocal.bat (or FontFinderLocal.exe). Keep `_internal` beside the executable. Stop with Stop-FontFinderLocal.bat or Ctrl+C in the console. See `packaging/README.md` for rebuilding and validation.
