# Step 2 progress and recovery

## Baseline (2026-10-14)

- Step 1 is protected. Inspected `app/api.py`, discovery/metadata/rendering, SQLite persistence, native startup, frontend modules and existing tests.
- Baseline command: `.venv\Scripts\python.exe -m pytest -q --basetemp=test-results/step2-baseline`.
- Result: **23 passed in 12.75s**, one existing Starlette/httpx deprecation warning.
- Initialized a local-only Git repository. Checkpoints use command-scoped identity/safe-directory settings because the sandbox user differs from the folder owner; no global Git configuration or remote is used.
- Runtime: Python 3.13.16; existing app at loopback port 8766; local metadata/favorites/settings stay in `data/`.

## Architecture decisions

- Add `app/matching/` services; reuse the existing Catalog, Renderer asset conversion, IDs, favorites and font-details actions. No second font scan.
- Direct FreeType + HarfBuzz for server-side exact-text rendering; Pillow for decoding and NumPy/OpenCV for deterministic geometry. No OCR, models, telemetry, or remote runtime calls.
- Controlled uploads with byte/pixel limits and expiring PNG storage under `data/matching-temp/`.
- One cancellable background matching worker, a bounded render cache, coarse whole-word screening then detailed alignment/tracking/contour scoring and conservative character-aware scoring.
- Separate additive frontend modules for image editing, job/results, and comparison; preserve the Font Browser's styles and behavior.
- Exact text is never case-folded, corrected, or Unicode-normalized. Image/text/processing changes invalidate visible results.

## Current status

Baseline checkpoint: `dc3f446`. Core backend is implemented and integrated additively into `app/api.py`. Nine new matching tests pass (1.00s): supported image formats/EXIF/limits, exact text validation, glyph coverage/tracking, preprocessing, geometry/metrics, four comparison images, job APIs, shared favorites, independent text jobs, cancellation and single-worker admission. Resume instruction received during the same implementation pass; continue these files, do not recreate the project.

## Remaining

1. Secure upload/preprocessing and native exact-text rendering.
2. Multi-stage ranking, jobs, cancellation, comparison API and tests.
3. Additive Image Font Finder UI, crop/perspective/zoom, advanced processing, results and comparison.
4. Ground-truth accuracy evaluation, real runtime/browser workflow, Step 1 regression tests.
5. Documentation, limitations and final local checkpoint.

## Resume

Read this file and `git log`, inspect current changes; do not restart or discard work.
Run `.venv\Scripts\python.exe -m pytest -q --basetemp=test-results/step2-tests`.
Launch with `Start-FontFinderLocal.bat`; stop with `Stop-FontFinderLocal.bat` before backend changes are tested.

## Files/dependencies/tests

New: `app/matching/{models,images,preprocess,raster,metrics,engine,comparison,service,routes}.py`, `tests/test_matching.py`, this log.
Modified: `requirements.txt`, `requirements-lock.txt`, `app/api.py` (router/service lifecycle and local blob image CSP only).
Installed: Pillow 12.3.0, NumPy 2.5.4, OpenCV headless 4.14.0.94, freetype-py 2.5.1, uharfbuzz 0.56.3. Pillow reports no RAQM support on this machine, so direct FreeType/HarfBuzz is required instead of relying on Pillow text shaping. Update dependency lock after integration.
Frontend added: `frontend/matching.html`, `matching.css`, `matching.js`, `image-editor.js`. Existing `index.html` activates the navigation and mounts the new workspace; `app.js` adds narrow integration callbacks for shared favorites/details/comparison and navigation. No existing Browser styles were changed.

Integrated suite: **32 passed in 15.34s**, including all 23 Step 1 regression tests. JavaScript syntax checks pass. Independent Pillow-generated ground-truth benchmark is running (`python -m tests.benchmark_matching`); first five transformed cases ranked the exact originating face first. Do not extrapolate until the complete report is written.

Backend checkpoint: `88d34b7`. Current frontend is saved but not yet browser-verified/checkpointed. New backend started with logs in `test-results/step2-server-*.log`.
## Latest validation and fixes

- Independent benchmark completed: **10 transformed cases against 91 local faces; exact-ID top-1 90%, top-5 100%, top-10 100%; 46.05 seconds total**. Arial Narrow ranked third behind nearly equivalent compressed Arial faces. Report: `test-results/ground-truth/accuracy.json` (machine-local, not committed).
- Browser full-catalog search: 639 faces, 615 eligible, 23 missing-glyph exclusions, 1 render failure, **18.0 seconds**. For the transformed Arial sample, Arial ranked third/fourth behind Microsoft Sans Serif. Do not represent subset benchmark accuracy as full-library accuracy.
- Browser verified upload, processed preview, mixed-case text, native candidate previews, interactive crop (bounds changed), matching progress, cancellation, differences/overlay, manual position and Auto Align, shared details, favorites, add-to-comparison with exact text, case-only text change clearing results without reupload.
- Preserved the user's existing Browser settings/favorites in `test-results/step2-ui-baseline.json` before integration tests. **Restore these after browser testing**, so test text/comparison choices do not replace user preferences.
- Added transparent-white-letter/counter preservation, bounded-width-distortion, upload expiry, deterministic ranking tests. **13 matching tests now pass**; final complete suite still to run after latest fixes.
- Fixed active-upload cleanup, stale preview visibility, very short export labels, stale-font errors, early cancellation race, perspective-mode reset after rotation/crop reset. Latest frontend changes need reload for final verification.
- Remaining: documentation, runtime comparison/export and final regression validation, restore saved user preferences, local Git checkpoint. No OCR or executable packaging.
