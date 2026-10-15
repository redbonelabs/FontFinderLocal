# Font Browser preview layout correction

## Cause and scope

Reproduced with the saved `\nx5 MULTIPLIER ADVANCES` sample at 46 px in compact mode: the fixed single-line card left **85 px** for a preview whose two lines required **122 px**. Flex shrinking and `overflow:auto` created the internal vertical scrollbar. The virtual list also assumed identical single-line row heights. The relevant CSS and sample loader were identical to the approved Step 1 checkpoint `dc3f446`; these constraints were not introduced by Step 2 CSS.

Glyph ink can also exceed nominal font metrics. During validation, a CFF preview exposed a difference between canvas metrics and the browser's inline line boxes. Merely hiding vertical overflow or adding a larger constant height would leave these cases clipped.

Production changes are confined to:

- `frontend/fonts.js`: measure loaded glyph ink, variable-instance metrics and real DOM line boxes/baseline; reserve the needed overhang and multiline height. Preserve the entered text and the original visual padding. Use current settings when asynchronous font loading finishes.
- `frontend/styles.css`: prevent flex shrinking of the sample, allow horizontal scrolling, and remove internal vertical scrolling.
- `frontend/app.js`: use natural card height and observe measured row sizes; update cumulative offsets on font loading, text/size changes, width and density changes. Preserve the existing minimum card spacing/appearance.
- `frontend/preview-rows.js`: small cumulative-height index with binary viewport lookup, measured-height invalidation and stable scroll anchoring.

No discovery, persistence, backend matching, Image Font Finder code or dependency changes. The preview fields changed during live testing were restored. Favorites and custom-directory configuration were not changed by the main-application tests; destructive/stateful integration checks used isolated test data.

## Executed validation

- **38 Python tests passed in 15.87 seconds**, including all 23 original Step 1 tests and all 15 Step 2 matching cases. One existing Starlette/httpx deprecation warning, no failures.
- **Node virtual-row regression passed:** mixed measured heights, exact boundaries, tall rows, late height changes above the viewport, invalidation and empty lists.
- **90 browser glyph-layout cases passed:** sizes 24/46/72/126 and back to 24, single-line/multiline/leading-newline/long text, compact and comfortable density, normal and extreme decorative outlines, and a real generated variable font. The extreme A spans **2.2 em above and 0.8 em below its baseline** despite nominal 0.8/-0.2 em metrics. Bounds are checked against an independent DOM baseline marker and the known fixture outlines, not only scroll-height assertions. No vertical overflow; all 30 deliberately long cases retained horizontal overflow.
- Variable-axis contraction was checked at identical text and size, after expansion, without reloading the font asset. The actual application's axis slider also expanded both the library and details previews without clipping.
- Installed Windows fonts: Futura Book BT (TrueType), Futura Condensed and Futura Heavy (CFF) passed 24 → 46 → 72 → 126 → 24 with accented ascenders, descenders and two lines. All measured vertical overflow values were zero; adjacent virtual-row gaps remained at least the original 12 px.
- Custom-folder fonts: original decorative references were checked during reproduction; isolated custom-folder normal/tall/variable fixtures were verified through the actual application catalog, details and virtual list.
- Horizontal interaction was verified, not just CSS: a visible tall preview moved to **scrollLeft 1609.33 px**, while scrollTop and vertical overflow remained zero.
- Virtualized scrolling through later faces, asynchronous font loading, width changes to 820 px, density changes, comparison cards, favorite filtering and navigation between utilities were checked. Observed settled rows did not overlap. Comparison preview height shrank correctly when returning from 126 to 24 px.
- JavaScript syntax and Git whitespace checks passed.
- Live Step 2 regression: **642 faces / 617 eligible**, exact-text matching in **17.331 seconds**, native preview, four valid adjusted comparison PNGs, Auto Align and cancellation passed. The existing missing-glyph and unsupported-render exclusions remained explicit.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=test-results/preview-regression
node --test tests/test_preview_rows.mjs
.\.venv\Scripts\python.exe -m tests.preview_layout_server
```

Open the printed loopback address followed by `/preview-layout-check`, then click **Run sizes 24 / 46 / 72 / 126**. The fixture serves the production frontend with generated fonts and separate storage under `test-results/preview-layout/`. It never installs fonts or edits normal application preferences. Its ordinary `/` page can also be used to inspect library/details/comparison behavior. Font fixture files are generated locally and ignored by Git.

Browser checks used the Codex Chromium-based in-app browser on Windows. This is not an exhaustive cross-browser or every-installed-font certification. Refresh an already-open application page to load the corrected frontend; no backend restart or setup change is needed.
