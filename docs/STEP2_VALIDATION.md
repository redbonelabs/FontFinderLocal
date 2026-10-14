# Step 2 completion validation

Validated on Windows x64, Python 3.13.16, 2026-10-14. Step 2 is implemented and ready for Step 3 real-artwork refinement. The original Step 1 regression tests and visual styling remain protected. No OCR implementation, recognition dependency, remote processing, Git remote, push, or executable package was introduced.

## Executed checks

- Approved Step 1 baseline: **23 passed in 12.75 seconds** before implementation.
- Final complete suite: `python -m pytest -q --basetemp=test-results/step2-release` — **38 passed in 15.38 seconds**: 23 original regressions and 15 matching cases, including the two alignment-anchor cases. One existing Starlette/httpx deprecation warning; no failures.
- Targeted matching suite after export changes: **15 passed in 0.82 seconds**.
- `node --check` passed for the application, matching and editor modules. `python -m pip check` found no broken requirements.
- Live Step 1 API checks: **639 faces / 398 families**, 1,117 cached files, no discovery issues. Valid actual TTF, CFF, variable and extracted TTC assets and metadata were retrieved.
- Live matching API: exact text `"  Supreme!  "`, 639 faces screened, 614 eligible, 24 missing-coverage exclusions, one render failure; **18.987 seconds**. Actual previews, four adjusted comparison PNGs, Auto Align and cancellation passed. The excluded face is reported, never replaced by fallback glyphs.
- Final browser run: upload, processing, exact text, whole-library search (**19.0 seconds**), 20 actual result previews, inspection, and PNG attachment download succeeded. A warm-cache browser run took 4.1 seconds; timings are specific to this machine/sample.
- Browser observations across the implementation pass include interactive cropping, perspective/reset, progress/cancel, case-only text edits clearing rankings without reupload, all comparison modes, manual position and Auto Align, shared favorite/details/comparison actions. Desktop and 800-pixel workspace layouts were visually inspected. The original Browser settings and favorites were restored and verified.
- Startup and normal authenticated shutdown/restart succeeded after an old unresponsive development process was stopped. No startup source changes were needed; the later normal lifecycle completed cleanly.

## Completion criteria audit

| Original criterion | Implementation and evidence |
|---|---|
| 1. Step 1 functional | All 23 original tests pass; live catalog/assets and Browser preference restoration verified. |
| 2. Upload images | Browser upload; actual-content decoding tests for PNG/JPEG/BMP/TIFF/WebP. |
| 3. Crop/preprocess | Interactive crop and previews observed; crop, polarity, transparency, color, counters and invalid perspective tests. Independent perspective benchmark. |
| 4. Exact text required | Disabled Find button until image and visible text exist; server validation. |
| 5. Text unmodified | Case, punctuation, repeated letters, spaces and decomposed Unicode assertions. Captions retain whitespace visually. |
| 6. Edit without reupload | Browser case-only edit retains image and removes old results; independent immutable API jobs. |
| 7. Exact candidate rendering | Direct HarfBuzz/FreeType rendering; no alternate-case strings or fallback fonts. Native result previews observed. |
| 8. Missing glyphs | Coverage and shaped-glyph checks; rejection tests and real catalog exclusion counts. |
| 9. Geometric ranking | Coarse screening, bounded alignment/tracking, overlap/contour/structural/projection metrics and conservative character evidence; measured benchmark below. |
| 10. Actual previews | Real renderer PNGs in browser cards and live API checks. |
| 11. Inspect candidates | Browser comparison dialog, diagnostics and shared metadata. |
| 12. Side by side | API generation and browser visual inspection. |
| 13. Overlay | API generation and browser visual inspection. |
| 14. Difference/outline | API generation and browser visual inspection. |
| 15. Alignment controls | All transform options exercised by live API; browser manual X and Auto Align; left/right anchor regression tests. Reset restores automated fit; ranking is immutable. |
| 16. Progress/cancel | Browser progress/cancel, real API cancellation, worker admission/cancellation tests. |
| 17. Shared integration | Existing IDs/store reused; browser favorite/details/add-to-comparison verified. Copy/Locate delegate to existing platform mechanisms; limits below. |
| 18. Common image problems | EXIF, transparency, low contrast, noise, outlines, skew, perspective and cropped-boundary handling; warnings/manual color controls. Complex artwork remains an accuracy limitation. |
| 19. Responsive UI | Background worker; browser controls usable while searching; bounded caches/concurrency and responsive layout inspected. |
| 20. Security/privacy | Existing loopback/Host/Origin/token guard retained. Upload/content/dimension/path/expiry tests. Local assets only. |
| 21. Tests pass | Final 38-test suite, live APIs, browser workflow and independent benchmark executed. |
| 22. Existing behavior unchanged | Additive integration only; original Browser CSS, font loading, discovery, store and startup unchanged. Preferences restored after tests. |
| 23. No OCR | Source/dependency inspection: manual text is the sole authoritative input; no recognition UI or service. |
| 24. Ready for Step 3 | User guide, algorithm notes, repeatable tests/benchmark, limitations and local recovery checkpoints provided. |

## Independent accuracy benchmark

`python -m tests.benchmark_matching` generated references independently with Pillow and transformed them before matching against **91 installed faces**, including similar styles and duplicate binaries. Ten cases covered scaling, rotation, noise, outlines, low contrast, tracking, perspective and crop variation, with mixed case, repeated letters and punctuation.

| Metric | Measured result |
|---|---:|
| Exact originating catalog ID top-1 | 9/10 — 90% |
| Exact originating catalog ID top-5 | 10/10 — 100% |
| Exact originating catalog ID top-10 | 10/10 — 100% |
| Combined matching time | 46.05 seconds |

Arial Narrow ranked third behind similar scaled faces. This small synthetic subset is **not** a full-catalog or real-pinball-artwork accuracy claim. The complete 639-face browser searches showed near-ties among Arial/Microsoft Sans Serif. The UI describes scores as relative geometry matches, never probabilities or proof of identity.

Local reports/images live under ignored `test-results/`: `ground-truth/accuracy.json`, `runtime-api.json`, `runtime-matching.json`, and `comparison-*.png`. No installed font binaries are committed.

## Limitations and unverified behavior

- Same-color attached shadows, heavy distress, multistroke/embossed effects and curved artwork may require better references/manual isolation. No real pinball evaluation corpus was supplied.
- Variable fonts use the default and bounded representative named instances, not continuous axis optimization. Single-direction text runs are shaped; mixed-direction paragraph layout, multiline/vertical text and all color/bitmap glyph formats are unsupported. The UI requests one line/typeface, at most 160 characters.
- Full-library duplicate or nearly equivalent fonts may tie. One real catalog face failed native rendering and was excluded in the recorded search.
- Native font processing runs in a bounded thread, not a crash-isolated subprocess. Cancellation occurs between native operations. Very large libraries and pathological fonts have not been stress-tested.
- Browser PNG download was verified after replacing blob-based export with an HTTP attachment. Other browser families and their save-dialog behavior have not been tested here. Native Windows Explorer focus/selection and OS clipboard effects were not manually reverified during Step 2; their existing validated mechanisms remain in use.
- Drag-and-drop, every pointer/keyboard combination, all advanced-control combinations and assistive-technology behavior were not exhaustively browser-tested. Their underlying upload/processing operations have automated coverage.
- Editing sessions are temporary and are not restored after reload/restart. The original upload is retained in controlled expiring local storage; original user files are never edited.

No mandatory Step 2 feature is left unimplemented. Next work should measure difficult real artwork before changing scoring, rather than treating these synthetic results as general accuracy.
