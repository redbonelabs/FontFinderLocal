# Roadmap

## Step 2: implemented

Local upload/preprocessing, mandatory exact-text shaping, whole-library screening and detailed ranking, progress/cancellation, four visual comparison modes, alignment/export and shared Font Browser actions. See `IMAGE_FONT_FINDER.md`, `MATCHING_ARCHITECTURE.md`, `STEP2_VALIDATION.md` and `../STEP2_PROGRESS.md` for evidence and recovery state. Step 1 remains protected by its regression suite.

## Next milestone: real-artwork refinement

1. Build a labeled local pinball-lettering evaluation corpus with outlines, shadows, worn paint, perspective, metallic effects, curved lettering and near-identical faces. Record top-1/top-5/top-10 by difficulty with source permissions.
2. Improve same-color attached shadow and multistroke outline separation while preserving counters and thin details.
3. Refine tracking and native-proportion optimization using measured errors, particularly condensed-versus-scaled designs.
4. Add continuous variable-axis optimization and script-aware segmentation only where ground truth shows a benefit.
5. Expand keyboard perspective editing, accessibility, touch, cross-browser downloads and large-library performance tests.
6. Consider saved image sessions/presets with explicit retention controls.

Reference text remains manually supplied and authoritative. No automatic text-recognition stage or external model service is planned.

## Later: distribution and hardening

- Bundle Python, native rendering dependencies, and static frontend into a portable Windows distribution; add signed-release and clean-machine testing.
- Test startup/shutdown, multi-monitor/browser scaling, complex-script shaping, color fonts, and large CJK collections across supported browsers.
- Move untrusted font parsing into supervised subprocesses with resource limits.
- Add optional directory watching, import/export of settings, saved comparison collections, and accessible keyboard shortcuts.
- Add measured indexing/performance benchmarks and incremental catalog delivery for exceptionally large libraries.
