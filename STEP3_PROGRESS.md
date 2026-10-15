# Step 3 progress and recovery

## Status: complete — 2026-10-15

Step 3 benchmarking, refinement, acceptance evaluation, regression/browser validation and reporting are complete. Stop development for this milestone. Read `STEP3_ACCURACY_REPORT.md` for methodology, measured results, limitations and the next recommended work.

Protected baseline: `101638d`. Accepted production implementation: `7968442`; the final evidence/documentation checkpoint follows this update. No OCR, remote/push, packaging, dependency change, interface redesign or Font Browser modification was introduced.

## Accepted results

Frozen full catalog: 642 installed faces / 401 families; 40 known-origin references using 36 faces, plus four separate absent/altered probes. Twenty development and twenty held-out cases. Stable seed, independently generated Pillow references, frozen image hashes and catalog IDs. No custom folders were configured. Do not regenerate the dataset or repeat completed benchmark runs.

| Evaluation | Strict baseline top-1/5/10 | Accepted top-1/5/10 | Mean search time baseline → accepted |
|---|---|---|---|
| Development (20) | 75% / 100% / 100% | 80% / 100% / 100% | 17.7908s → 5.45095s |
| Held-out (20) | 80% / 95% / 95% | 80% / 95% / 95% | 18.08475s → 5.52175s |
| Combined (40) | 77.5% / 97.5% / 97.5% | 80% / 97.5% / 97.5% | 17.937775s → 5.48635s |

Mean runtime decreased 69.4%. Only one correct-face rank changed: development Arial Bold synthetic artwork improved 2 → 1. All other development/held-out ranks stayed unchanged. Exact text-specific raster-equivalence top-1 is separately 85% → 87.5% combined; strict metrics are not replaced by this supplemental audit.

**Use `benchmarks/results/accepted-*.json` as the final results.** Historical `final-*.json` files are a rejected regularization experiment, retained for audit, not the accepted implementation. `baseline-*.json` is preserved untouched. `equivalence-baseline-accepted.json` is the supplemental exact-pixel audit.

## Production changes

- `app/matching/raster.py`: read native TTF/OTF/TTC bytes directly, preserving collection face index, instead of rebuilding font tables/checksums. Web fonts retain shared conversion; freshness checks and bounded cache remain. No shared browser renderer change or new cache.
- `app/matching/metrics.py`: crop once and resize once per scale, reuse for translations. Grid, score weights and comparison geometry unchanged.
- `app/matching/engine.py`: add bounded tracking half steps only when reference ink spans reliably agree with the supplied sequence. Uncertain/joined masks retain the baseline three-value search. No spacing penalty remains. No text recognition or correction.

Unrestricted fine spacing introduced a thin-font near-tie regression; a spacing penalty subsequently degraded the low-resolution case. Both were revised on development evidence. Held-out results did not select parameters. No preprocessing change was justified by the development evidence.

## Completed validation

- 43 Python tests passed in 15.27s, including all 23 original Step 1 tests. One existing Starlette/httpx deprecation warning; no failures. Node virtual-row test, JavaScript syntax and pip dependency check passed.
- Native optimization audit: 626 identical face/instance renders and 23 identical exclusions; no differences. All 135 baseline-versus-optimized score/alignment cases identical.
- Clean authenticated shutdown/restart. Live catalog/browser asset checks passed for TTF/CFF/TTC/variable fonts, 1,120 cached files, no scan issues.
- Live matching: exact `"  Supreme!  "`, 617 eligible faces, 6.141s, four adjusted comparison PNGs, Auto Align and cancellation passed.
- Browser upload → manually entered exact text → progress → ranked results → comparison verified. All four views, eight manual controls, Auto Align/reset and actual PNG download observed. Case-only text edit invalidated results without replacing the image. No browser errors/warnings.
- Preview correction: 90 browser glyph-layout cases passed (24/46/72/126/back-to-24, extreme decorative bounds, actual variable gvar geometry, multiline/leading newline, both densities). Zero vertical overflow; all 30 long cases retained horizontal overflow. Installed TTF/CFF multiline previews passed repeated sizes; virtual-row gaps remained above 12.66px.
- Browser test tabs closed and isolated preview server stopped. Original settings restored and verified; favorites/folders unchanged. Main application remains running at http://127.0.0.1:8766.
- Machine-readable validation: `benchmarks/results/validation.json`. Detailed live logs/artifacts are in ignored `test-results/`.

## Known limitations / next milestone

One held-out gradient-background case still fails automatic polarity; the existing Dark lettering option restores rank 1 in a separate diagnostic excluded from acceptance metrics. Small hinted lettering and similar/aliased outlines remain ambiguous. Absent-original probes do not establish calibrated open-set rejection. All artwork is synthetic; no real photographs/user artwork were tested. Current catalog has no custom folders; no thousands-of-fonts or cross-platform certification.

Next recommended work: collect a new untouched labeled real-artwork evaluation set, with custom libraries, gradient backgrounds and small text, plus human Top-10 usefulness judgments. Use a separate new development split for polarity work. No required Step 3 work remains.

## Checkpoints and recovery

- `f560425`: frozen benchmark before algorithm changes.
- `bce9398`: complete baseline measurements and native-rendering tests.
- `32c3ed1`: native/alignment optimization and intermediate spacing experiment.
- `7968442`: accepted conservative spacing implementation, frozen before acceptance runs.
- Final evidence/report checkpoint: inspect `git log -1` after this update. No remote is configured.

Launch: `Start-FontFinderLocal.bat`, or `.\.venv\Scripts\python.exe -m app.startup --no-browser`. Stop with `Stop-FontFinderLocal.bat`. Benchmark reproduction commands and exact equivalence policy are in `benchmarks/README.md`. Generated local images/catalog snapshots are Git-ignored; proprietary font files are not bundled.
