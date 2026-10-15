# Step 3 accuracy and performance report

Completed 2026-10-15 on Windows, Python 3.13.16. Accepted matching implementation: local checkpoint `7968442`. The accepted result files are **`benchmarks/results/accepted-*.json`**. Files named `final-*.json` are a preserved, rejected intermediate experiment; they are not the release results.

## Measured outcome

| Evaluation | Cases | Baseline top-1 / top-5 / top-10 | Accepted top-1 / top-5 / top-10 | Mean search time, baseline → accepted |
|---|---:|---|---|---|
| Development | 20 | 75% / 100% / 100% | **80% / 100% / 100%** | 17.791s → **5.451s** |
| Held-out | 20 | 80% / 95% / 95% | **80% / 95% / 95%** | 18.085s → **5.522s** |
| Combined descriptive total | 40 | 77.5% / 97.5% / 97.5% | **80% / 97.5% / 97.5%** | 17.938s → **5.486s** |

These are strict catalog-face-ID results. Exactly one rank changed: the development Arial Bold synthetic artwork improved from second to first. Every other development and held-out correct-face rank stayed unchanged. Thus there was a modest development accuracy improvement and no observed held-out accuracy regression, **not evidence of a statistically established general accuracy gain**. Mean cold search runtime fell **69.4%** (3.27× faster) on this dataset and machine.

| Additional combined metric | Baseline | Accepted |
|---|---:|---:|
| Median search time | 18.242s | 5.366s |
| 90th percentile search time | 20.541s | 6.847s |
| Median correct-face rank among retrieved faces | 1 | 1 |
| Correct faces not retrieved in the 60-face shortlist | 1 / 40 | 1 / 40 |
| Maximum sampled process working set | 171.25 MiB | 138.38 MiB |
| Missing-glyph exclusions, summed across searches | 1,013 | 1,013 |
| Rendering failures, summed across searches | 4 | 4 |

All ordinary searches considered **642 faces**; 545–623 were eligible depending on the exact supplied text. Exclusion totals count repeated face/search events, not unique fonts. Memory is a working-set sample after each search, not a true peak measurement or the entire desktop application's footprint.

## Methodology and coverage

- Frozen actual local catalog: 642 installed faces / 401 families. The 40 known-origin references use **36 distinct faces**, including sans, serif, script, decorative, condensed, extended, bold, thin, italic, monospace and variable cases. Near-neighbor faces and duplicate-name binaries remain in the candidate pool. No custom folders were configured, so no custom-folder accuracy claim is made.
- Twenty development cases and twenty held-out cases use different font/text pairs. Fonts/families are not all disjoint between splits. Four separate probes cover two removed-origin cases and two deliberately altered lettering cases. Probes are excluded from ordinary identification accuracy.
- Exact strings include mixed case, punctuation, repeated letters, numbers, accented Unicode and doubled/edge spaces. Strings are never normalized, corrected or recognized automatically. The manually supplied string is rendered for every candidate.
- References use independent Pillow BASIC layout and hinted rasterization at source sizes 24–126 px, with selected supersampling/downsampling. Candidates use HarfBuzz shaping and unhinted FreeType rendering at 96 px. Both pipelines use FreeType underneath; this is independence of rendering pipeline/settings, not independent raster libraries. No candidate masks generate references.
- Stable seed `20261014`; image SHA-256 hashes, exact catalog IDs, options and source strata are retained in `benchmarks/datasets/manifest.json`. Generated images and full local-path catalog snapshots are ignored by Git. No font binaries are bundled.
- Every timed case starts with empty application raster/asset caches. Operating-system disk caches and background Windows activity are uncontrolled. Baseline and acceptance use the same frozen references, candidate files, shortlist, sensitivity and processing options. Performance comparisons use `match` runtime; preprocessing and total wall time are separately saved.
- Baselines were saved before production changes. Development evidence selected the changes. A regularization experiment was rejected because development top-5 fell; held-out failures were not used to tune parameters. No weights were fit to the held-out set. All measured runs remain available.

## Ambiguous identities

The primary metrics require the exact face ID. The manifest also records very conservative identical-outline/shaping/metric-table equivalence; this did not change the headline results.

A separate audit checks exact pixels, bounds and advances at **two Pillow sizes (64/127 px)** plus exact HarfBuzz-shaped native pixels, advance and glyph count at 96 px. No pixel tolerance, score tolerance or family-name grouping is permitted. This is equivalence only for the supplied text and coordinates; it does not establish interchangeability for other letters or languages. Only observed top-ten candidates are audited.

| Exact text-specific equivalence | Baseline top-1 / top-5 / top-10 | Accepted top-1 / top-5 / top-10 |
|---|---|---|
| Development | 80% / 100% / 100% | 85% / 100% / 100% |
| Held-out | 90% / 95% / 95% | 90% / 95% / 95% |
| Combined | 85% / 97.5% / 97.5% | 87.5% / 97.5% / 97.5% |

These supplemental numbers are not substituted for strict accuracy. Some Windows faces share Latin outlines; other close/tied scores failed the stringent equivalence audit and remain ordinary strict failures. Evidence: `equivalence-baseline-accepted.json`.

## Accuracy by reference category

Strict top-1 results; top-5/top-10 are unchanged in every category. Each distorted category has only two samples, so these percentages are descriptive and have high uncertainty.

| Category | Cases | Baseline → accepted top-1 | Accepted top-5 / top-10 | Mean seconds, baseline → accepted |
|---|---:|---|---|---|
| Clean | 8 | 87.5% → 87.5% | 100% / 100% | 17.66 → 5.41 |
| Variable instance | 2 | 50% → 50% | 100% / 100% | 18.91 → 5.41 |
| Cropped margins | 2 | 100% → 100% | 100% / 100% | 17.63 → 6.12 |
| Outline | 2 | 100% → 100% | 100% / 100% | 16.05 → 5.07 |
| Shadow | 2 | 100% → 100% | 100% / 100% | 18.30 → 7.37 |
| Noise | 2 | 100% → 100% | 100% / 100% | 18.58 → 4.99 |
| Rotation / deskew | 2 | 100% → 100% | 100% / 100% | 18.71 → 5.22 |
| Low contrast | 2 | 50% → 50% | 100% / 100% | 16.72 → 4.73 |
| Colored fill | 2 | 100% → 100% | 100% / 100% | 15.41 → 4.94 |
| Tracking | 2 | 100% → 100% | 100% / 100% | 20.78 → 6.13 |
| Horizontal stretch | 2 | 100% → 100% | 100% / 100% | 19.94 → 8.15 |
| Uncorrected mild perspective | 2 | 50% → 50% | 100% / 100% | 19.23 → 5.51 |
| Layered synthetic artwork | 2 | **50% → 100%** | 100% / 100% | 16.93 → 4.99 |
| Low resolution | 2 | 50% → 50% | 100% / 100% | 19.51 → 6.14 |
| Antialias/resampling | 2 | 0% → 0% | 100% / 100% | 20.32 → 6.06 |
| Inverted polarity | 2 | 100% → 100% | 100% / 100% | 14.80 → 3.46 |
| Gradient background | 2 | 50% → 50% | 50% / 50% | 16.29 → 3.82 |

Each complete JSON report additionally contains breakdowns by font type, exact text, quality, source size and installed/custom source classification, with ranks, component scores, exclusions and top-ten candidates for individual cases.

## Targeted changes and guardrails

1. **Native matching asset preparation.** Profiling 80 faces attributed 2.124 of 2.312 seconds to shared asset preparation, largely table checksum recomputation. Matching now feeds original native TTF/OTF/TTC bytes directly to FreeType/HarfBuzz, preserving the collection face index. Web-font formats keep the existing sfnt conversion. Catalog freshness checks and bounded raster caching remain; no extra cache, parallel worker or dependency was added. The shared Font Browser asset renderer is unchanged.
2. **Alignment allocation reduction.** Crop the candidate once and resize once per scale, then place that image for each translation. The bounded scale/translation grid, score weights and comparison geometry are unchanged. All 135 comparison cases against the protected implementation produced exactly equal scores, metrics and alignment.
3. **Conservative finer spacing.** Add half steps inside the existing tracking range only when reference ink spans agree with the supplied sequence using the existing geometric segmentation. Joined/uncertain text keeps the original three-value whole-word search. No OCR, expanded distortion allowance or text modification. The synthetic Arial Bold artwork improves rank 2 → 1.

The unrestricted half-step experiment gained one development match but lost a thin-font near tie. A subsequent spacing penalty preserved top-1 but pushed low-resolution Calibri from rank 3 to 7. Both were rejected or revised. The accepted implementation has **no spacing penalty**, and all other correct-face ranks remain unchanged. Preprocessing was retained because the development evidence did not justify a broad replacement.

Full-catalog rendering equivalence checked 649 face/instance attempts: **626 identical renders and 23 identical exclusions**, with no differences in pixels, advances or glyph counts. This includes actual local collection faces, CFF and variable fonts. The 23 exclusions in that audit are for its one test string and differ from the multi-case benchmark exclusion totals.

## Failure analysis and practical limits

- **Reference preprocessing:** the gradient-background Cambria Bold case selects the wrong automatic polarity, fills much of the frame and loses the origin before final ranking. Existing crop-boundary/foreground-density warnings appear. A separate post-evaluation diagnostic using the existing **Dark lettering** option returns the origin at rank 1. This result is excluded from all acceptance metrics, and preprocessing was not tuned to this held-out case.
- **Rendering/normalization discrimination:** clean small Arial and low-resolution Calibri still favor similar faces. Source hinting, antialiasing and lost low-resolution detail limit discrimination against the 96-pixel native candidate. Neither failure is hidden as an alias.
- **Identity ambiguity:** several differently named Windows fonts are exactly identical for the tested letters. Inspect more distinguishing characters; a high shape score cannot establish an exact file identity.
- **Absent/altered probes:** removing the origin and its table-identical group still leaves an Arial variant that scores 90.70. This probe tests file-ID absence, not guaranteed absence of all visually identical lettering. Removing Georgia produces Century at 68.42 (baseline 67.02), with near-tie guidance; its top ten are suggestions, not validated substitutes. Warped Impact and Jokerman remain first at 75.02 and 72.49, respectively. The interface labels all scores relative similarity and never declares these exact matches. These probes do **not** establish calibrated open-set rejection or subjective Top-10 usefulness on real artwork.
- No real pinball photograph, scanned print or user artwork was tested. All artwork/photo-like effects are synthetic. Full paragraph shaping, complex mixed-direction/multiline matching, continuous variable-axis fitting, hard native-font timeouts and difficult same-color effects remain outside this validated scope. The 642-face catalog is not a thousands-of-faces stress test.
- Font Browser multiline preview is supported and tested; Image Font Finder still intentionally accepts one exact text line. Current accuracy-source coverage is installed fonts only. Cross-platform/browser behavior and every original UI control combination were not exhaustively retested.

## Regression and application validation

- Full Python suite: **43 passed in 15.27s**, including all 23 original Step 1 tests, the Step 2 suite and new collection/variable/cache/native-equivalence/spacing checks. One existing Starlette/httpx deprecation warning; no failures. Node virtual-row regression, JavaScript syntax checks and `pip check` passed.
- Authenticated shutdown and clean application restart succeeded. Live catalog: 642 faces / 401 families, 1,120 cached files, no scan issues. Actual TTF, CFF, variable and extracted TTC browser assets verified.
- Live exact-text API search `"  Supreme!  "`: 6.141s, 617 eligible, 24 missing-glyph exclusions and one unsupported rendering. Four adjusted comparison PNGs, Auto Align and actual cancellation passed.
- Browser workflow: upload synthetic artwork, manually enter `PINBALL`, observe progress, obtain 20 initial ranked previews with Arial Bold first (82.8, 5.2s). Overlay, difference, side-by-side, outline, all eight manual controls, Auto Align, reset and actual PNG attachment download verified. Changing only case to `Pinball` cleared rankings while retaining the image. No console errors/warnings observed.
- Protected preview regression: **90 browser cases passed**, covering 24/46/72/126/back-to-24 px, tall decorative bounds, real variable glyph expansion/contraction, multiline/leading-newline text and both densities. Maximum vertical overflow zero; all 30 long cases retained horizontal overflow. Installed Futura TTF/CFF faces also passed repeated sizes with three-line accented/descender text; measured virtual-row gaps stayed above 12.66px and heights contracted correctly.
- Test tabs closed, isolated layout server stopped, original preview settings restored and verified. Favorites and custom-folder configuration remain unchanged. Production frontend, discovery, shared browser renderer and dependencies have no Step 3 changes.

Machine-readable evidence: `benchmarks/results/validation.json`, `optimization-equivalence.json`, `accepted-*.json`, `equivalence-baseline-accepted.json` and `manual-polarity-diagnostic.json`. Detailed live artifacts remain in ignored `test-results/`.

## Completion and next work

All Step 3 acceptance criteria are satisfied: repeatable frozen benchmark; preserved baseline; classified weaknesses; targeted measured changes; held-out evaluation; top-k/runtime reporting; no observed rank regressions; both utilities and preview correction validated; complete report; no OCR, redesign, GitHub work or executable packaging.

The next recommended work is a **new, untouched evaluation dataset with labeled real artwork**, including custom-folder libraries, gradient backgrounds and small hinted text. Develop polarity improvements on a separate new development split, retain the present held-out evidence, and measure open-set/Top-10 usefulness with human judgments. No required Step 3 implementation work remains.

Launch with `Start-FontFinderLocal.bat` or `.\.venv\Scripts\python.exe -m app.startup --no-browser`. The validated application is currently running at `http://127.0.0.1:8766`. See `benchmarks/README.md` for reproducible commands; do not regenerate the frozen dataset or overwrite preserved reports.
