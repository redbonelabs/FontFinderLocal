# Step 3 progress

Protected starting checkpoint: `101638d` (completed Step 2 and verified Font Browser glyph/virtual-row correction). No user changes were present. No remote, OCR, packaging or UI redesign work.

## Baseline checks

- Full existing Python suite: 38 passed in 13.64 seconds; one existing Starlette/httpx deprecation warning.
- Node preview-row test: passed.
- Inspected catalog, shared rendering, matching rasterizer, preprocessing, metrics, ranking, API and prior validation documentation.
- Live catalog: 642 faces. Benchmark freezes this actual catalog without changing settings/folders.

## Current work

New independent Pillow reference harness: 20 development cases, 20 held-out cases, four absent/altered-lettering probes (subject to explicitly reported unavailable fonts). All 642 catalog faces participate; no origin-biased distractor sampling. Frozen images/catalog are ignored; compact manifest and measured reports are retained. Conservative table-identical geometry equivalence is reported separately from strict face identity. Cold application caches per case, stable seed, per-category results and sampled Windows working set.

Next: generate/freeze dataset, preserve baseline results before changing production algorithms; investigate development failures, then evaluate targeted changes and run held-out/regression/UI checks. No algorithm changed yet.
