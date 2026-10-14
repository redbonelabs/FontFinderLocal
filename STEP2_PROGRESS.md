# Step 2 progress and recovery

## Current status — complete, 2026-10-14

Step 2 is implemented and verified against all 24 original completion criteria. Stop feature development for this milestone. The next action is Step 3 evaluation on labeled real pinball/artwork references, followed by measured accuracy improvements. See `docs/STEP2_VALIDATION.md` for the criterion-by-criterion evidence and explicit unverified behavior.

Step 1 remains locked: original Browser styling, discovery, rendering, persistence and startup code are preserved; integration changes are additive. User Browser preferences and favorites captured before UI tests were restored and verified. No OCR, remote processing, GitHub work, or executable packaging was added.

## Working features

- Validated PNG/JPEG/BMP/TIFF/WebP uploads, EXIF orientation, byte/pixel limits, controlled expiring temporary storage.
- Crop, zoom/pan, rotation, four-corner perspective, restore/reset, manual color selection and processed/original previews.
- Mandatory exact case-sensitive text; case, punctuation, character order, repeated letters, spaces and Unicode input remain authoritative. Edits invalidate results without reupload.
- Shared catalog; native FreeType/HarfBuzz rendering with glyph-coverage checks, collection extraction and supported variable instances.
- Whole-catalog coarse screening, bounded detailed alignment/tracking, contour/overlap/structural/projection scoring, conservative character evidence and balanced repeated-letter weight.
- One background worker, progress/cancellation, bounded caches, stale catalog handling and useful warnings.
- Ranked native previews, initially 20 results, more results, favorites/category filters and metric diagnostics.
- Side-by-side, overlay, difference and outline comparison; all alignment controls, Auto Align, reset and local PNG export. Manual adjustments do not change ranks.
- Shared favorites/details/comparison, Open in Font Browser, Copy name and safe Locate file actions.
- User guide, algorithm documentation, accuracy benchmark and completion audit.

## Latest defects resolved

- Preserved the scoring anchor for left/right-aligned comparison and Auto Align; regression coverage added.
- Replaced blob-based export (download not observed in the in-app browser) with a validated local HTTP attachment. Actual browser download event verified.
- Fixed active-upload expiry, transparent white-letter visibility, stale previews/results, early cancellation, perspective reset, editor help after reset, and visual whitespace in exact-text captions.
- The old development server was unresponsive after interruption; only its verified project process was stopped. Subsequent authenticated shutdown and restart completed normally.

## Executed validation

- Original baseline: 23 tests passed in 12.75 seconds.
- Final full suite: **38 passed in 15.38 seconds**, including all 23 Step 1 tests and 15 matching cases. One existing Starlette/httpx deprecation warning; no test failures.
- Targeted matching suite after final export change: 15 passed in 0.82 seconds. JavaScript syntax checks and pip dependency check passed.
- Independent transformed ground truth: 10 cases / 91 faces; exact-ID top-1 90%, top-5 100%, top-10 100%; 46.05 seconds combined. Arial Narrow ranked third. Not a full-library or real-artwork accuracy claim.
- Real API: 639 faces, 614 eligible for `"  Supreme!  "`, 24 missing-coverage exclusions, 1 render failure; 18.987 seconds. Four valid adjusted comparison PNGs, Auto Align and cancellation verified.
- Final browser: upload through exact text/search/ranked previews/comparison/download verified. Full search 19.0 seconds; warm-cache run 4.1 seconds. Crop, case-change invalidation, shared integration and 800-pixel layout observed.
- Live Step 1 API: 639 faces / 398 families; actual TTF, CFF, variable and extracted collection assets validated, no scan issues.
- User settings/favorites restored from `test-results/step2-ui-baseline.json`; custom directories untouched.

## Remaining limitations (Step 3 work)

No required Step 2 feature remains unimplemented. Difficult real artwork, continuous variable-axis fitting, complex mixed-direction/multiline text, cross-browser/platform behavior and large-library stress testing remain refinement/validation work. Same-color attached effects may require manual isolation. One unsupported face was excluded during the measured live run. Clipboard/Explorer OS effects and every UI interaction combination were not manually reverified. Details are in the validation document.

## Files and architecture

New backend: `app/matching/{models,images,preprocess,raster,metrics,engine,comparison,service,routes}.py` with shared Catalog/Renderer/store integration in `app/api.py`. New frontend: `matching.html`, `matching.css`, `matching.js`, `image-editor.js`; narrow navigation/integration additions in `app.js` and `index.html`.

Added dependencies: Pillow 12.3.0, NumPy 2.5.4, OpenCV headless 4.14.0.94, freetype-py 2.5.1, uharfbuzz 0.56.3. Requirements and lock updated. Pillow lacks RAQM on this machine; direct HarfBuzz/FreeType provides native shaping.

Tests: `tests/test_matching.py`, `tests/benchmark_matching.py`, `tests/runtime_matching.py`; original Step 1 tests unchanged. Documentation: README, roadmap, architecture, new image finder guide, matching architecture and Step 2 validation.

## Recovery / launch

Local Git checkpoints: `dc3f446` protected Step 1 baseline; `88d34b7` matching backend; `dfc7719` integrated workspace and benchmark. The final completion checkpoint follows this update; inspect `git log -1`. No remote is configured. Never reset or discard user work.

This checkout is already provisioned. Double-click `Start-FontFinderLocal.bat` and choose Image Font Finder. Use `Stop-FontFinderLocal.bat` to stop it. Current validated address: http://127.0.0.1:8766 (launcher handles fallback ports).

Useful commands from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=test-results/step2-check
.\.venv\Scripts\python.exe -m tests.benchmark_matching
.\.venv\Scripts\python.exe -m tests.runtime_check
.\.venv\Scripts\python.exe -m tests.runtime_matching
```

Live checks require the server running; the matching live check uses `test-results/ground-truth/00-scale.png` produced by the benchmark. Generated images/reports/data and local runtimes are ignored by Git.
