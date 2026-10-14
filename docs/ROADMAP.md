# Roadmap

## Next milestone: Image Font Finder

1. Define a local reference-image workflow: crop, rotation, contrast, background removal, and optional known text.
2. Add safe image decoding with pixel/file limits and transparent progress/error reporting.
3. Introduce a local glyph rasterizer that accepts existing catalog IDs, collection indices, and variable coordinates. Build repeatable rendering tests first.
4. Implement deterministic baseline matching (alignment, normalized silhouettes, distance metrics), ranked candidates, and side-by-side overlays.
5. Cache versioned descriptors in SQLite, invalidate by content identity, and use cancellable bounded background jobs.
6. Evaluate on a documented corpus of synthetic and real lettering. Show uncertainty and explain that outlines, distortion, effects, and modified logos may not match a local font exactly.
7. Reuse favorites, details, comparison, and custom folders across both utilities.

No external model service or cloud dependency is planned. Add a local ML option only if evaluation demonstrates a concrete improvement and its model/license/distribution cost is acceptable.

## Later: distribution and hardening

- Bundle Python, native rendering dependencies, and static frontend into a portable Windows distribution; add signed-release and clean-machine testing.
- Test startup/shutdown, multi-monitor/browser scaling, complex-script shaping, color fonts, and large CJK collections across supported browsers.
- Move untrusted font parsing into supervised subprocesses with resource limits.
- Add optional directory watching, import/export of settings, saved comparison collections, and accessible keyboard shortcuts.
- Add measured indexing/performance benchmarks and incremental catalog delivery for exceptionally large libraries.
