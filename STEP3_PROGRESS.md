# Step 3 progress

Protected starting checkpoint: `101638d` (completed Step 2 and verified Font Browser glyph/virtual-row correction). No user changes were present. No remote, OCR, packaging or UI redesign work.

## Baseline checks

- Full existing Python suite: 38 passed in 13.64 seconds; one existing Starlette/httpx deprecation warning.
- Node preview-row test: passed.
- Inspected catalog, shared rendering, matching rasterizer, preprocessing, metrics, ranking, API and prior validation documentation.
- Live catalog: 642 faces. Benchmark freezes this actual catalog without changing settings/folders.

## Current work

New independent Pillow reference harness: 20 development cases, 20 held-out cases, four absent/altered-lettering probes (subject to explicitly reported unavailable fonts). All 642 catalog faces participate; no origin-biased distractor sampling. Frozen images/catalog are ignored; compact manifest and measured reports are retained. Conservative table-identical geometry equivalence is reported separately from strict face identity. Cold application caches per case, stable seed, per-category results and sampled Windows working set.

Dataset frozen and all baseline runs completed without algorithm changes. `benchmarks/results/baseline-{dev,heldout,probes}.json` are preserved. Development: 20 cases, strict top-1/5/10 75%/100%/100%, mean 17.7908s. Held-out: 20 cases, 80%/95%/95%, mean 18.08475s. Four probes completed separately. All cases used 642 candidates except absent-original probes. No unavailable reference faces. Current catalog has installed fonts only.

Three additional native rendering tests passed: distinct collection face outlines, actual variable gvar bounds/cache changes, exact-text/size/tracking and changed-file cache invalidation.

Development analysis: Arial clean ranks 3, Arial Bold artwork ranks 2, low-resolution Calibri ranks 3. Verdana/MS Reference Sans Serif and Segoe UI/Gadugi/Ebrima/Myanmar Text yield identical scores and masks; verify narrow text-specific equivalence separately without rewriting strict baseline measurements. Screening accounts for most cold runtime. Next: bounded spacing experiment, matching-only native asset preparation optimization, then full final development/held-out evaluation and regression/UI validation. Production algorithms are still unchanged.

## Refinement checkpoint

- Baseline preserved at `bce9398`; benchmark creation at `f560425`.
- Profiling 80 faces: 2.124/2.312 seconds spent in shared asset preparation, mainly font-table checksum recomputation. Matching now reads native TTF/OTF/TTC bytes directly, with the actual collection face index. Web formats retain the shared conversion fallback. Shared Font Browser renderer and frontend are unchanged; no extra cache added.
- Alignment now crops/resizes once per scale instead of once per translation; selection/scoring geometry is unchanged. Full-catalog rendering and 135 alignment equivalence checks are being run against the protected implementation.
- First development experiment (`candidate-dev.json`): half-step tracking corrected the artwork case but introduced a thin-font near-tie error; overall top-1 remained 75%, mean runtime 14.27665s. This run used native standalone sfnt optimization, before direct TTC support and spacing regularization.
- Revised automatic spacing applies a small 0.002-per-pixel cost relative to user-requested tracking, keeping explicit user spacing unpenalized. No scoring weights, preprocessing, shortlist size, text handling, or interfaces changed. Next: complete equivalence checks, freeze this revision, run full development and held-out final evaluations, then API/browser regressions.
- `audit_equivalence.py` supplements strict metrics with byte-identical Pillow pixels/bounds/advance at two sizes plus exact shaped native pixels/advance at 96px. It never broadens equivalence by family names or approximate scores and never edits preserved baseline reports.
