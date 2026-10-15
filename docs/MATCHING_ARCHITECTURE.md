# Image matching architecture

Step 2 is additive. `app/api.py` creates the matching service, mounts its router and manages its lifecycle. Existing catalog IDs, discovery, freshness checks, asset conversion, SQLite favorites, preferences, details and Explorer actions are reused. Step 3 leaves the approved Font Browser preview layout correction and its style sheet unchanged.

| Module | Responsibility |
|---|---|
| `matching/models.py` | Strict finite request schemas and exact-text validation without rewriting |
| `matching/images.py` | Content/byte/dimension validation, EXIF, generated IDs, controlled expiring storage |
| `matching/preprocess.py` | Crop, rotation, homography, alpha/color/luminance masks, conservative cleanup, alternatives, skew and ink bounds |
| `matching/raster.py` | Native sfnt/collection bytes (shared conversion for web fonts) → HarfBuzz positions/glyph IDs → FreeType alpha masks; coverage, variations, kerning and tracking |
| `matching/metrics.py` | Coarse features, bounded alignment, overlap, symmetric contour distance, local SSIM, projections and cautious character evidence |
| `matching/engine.py` | All-face screening, sampled variable instances, refinement, deterministic ranking and diagnostics |
| `matching/service.py` | One worker, progress/cancellation, immutable per-job inputs, temporary representations and cleanup |
| `matching/comparison.py` | Four visual modes and native PNG previews; adjustments do not mutate rankings |
| `matching/routes.py` | Scoped image/process/job/result/compare APIs; font IDs must belong to both job results and current catalog |
| `frontend/image-editor.js` | Reversible crop/pan/zoom/rotation/perspective and color selection |
| `frontend/matching.js/html/css` | Additive workspace, validation, stale-result rejection, results/comparison and narrow shared-browser callbacks |

## Algorithm

Screen every eligible face with the unchanged string. Reject missing glyphs and rendering failures. Preserve native ink metrics, then compare normalized coarse masks/projections and a small aspect term. Width is never a hard screening exclusion. Variable faces include the default and at most six representative named instances.

Refine the best 30–120 faces against primary and useful alternate masks. The original three tracking values remain the fallback for joined/uncertain lettering. When separated ink spans agree with the supplied character sequence, Step 3 adds two half steps without expanding the permitted range. This uses existing geometric segmentation, never text recognition. User-requested tracking remains the search center. Optimize residual scales/translations over a finite grid. Each candidate is cropped once and resized once per scale, then placed for each translation. Native aspect ratio constrains total horizontal correction to strict ±10%, balanced ±25%, or flexible ±40%. Extreme stretching cannot produce an unlimited fit.

Combine overlap (42%), symmetric contour similarity (30%), local structural similarity (16%) and projections (12%), with a small native-aspect penalty. If both images have separated Latin character runs agreeing with the supplied sequence, blend 8% character evidence. Average repeated occurrences within each exact character before averaging characters. Joined scripts and uncertain segmentation keep whole-word scoring. Break ties deterministically by catalog ID.

Scores are scaled to 0–100 and explicitly labeled relative shape matches. Poor scores, near-equal families, short samples, uncertain boundaries, clipped crops and preprocessing issues produce guidance. No text-recognition or correction stage exists.

## Lifetimes and security

The frontend increments an input version on relevant changes, clears old ranks, cancels obsolete jobs and rejects late responses. A separate processing version allows text-only changes to reuse the image. Backend jobs snapshot inputs/catalog revision; their results cannot silently switch text. One matching thread and one OpenCV thread bound CPU concurrency. Native raster cache: 48 MiB; shared asset cache: 32 MiB.

Uploads stream through a 20 MiB cap before decode. Formats come from actual bytes, dimensions are checked before decode, and decompression warnings fail closed. Decoding/processing run off the HTTP event loop. Generated paths and in-memory registries prevent arbitrary filesystem reads. Existing Host/Origin/token protections cover new routes. No image data enters the favorites database or external network.

The worker is a bounded thread, not a native-code sandbox. Hard per-font timeouts, full bidirectional paragraph layout, continuous variable-axis optimization, robust same-color effect separation and broader real-artwork evaluation are future refinements. No external service or executable packaging is part of this milestone.

## Step 3 reproducibility

`benchmarks/benchmark_runner.py` freezes the actual catalog and independently rendered Pillow references, then records full-catalog development/held-out/probe runs. The original scoring implementation remains recoverable at local checkpoint `101638d`; `bce9398` preserves all baseline reports before algorithm changes. `verify_optimizations.py` compares native output and alignment directly with that baseline. `audit_equivalence.py` reports exact text-specific raster duplicates separately from strict ID accuracy. See `STEP3_ACCURACY_REPORT.md` for measured results and limitations; scores remain relative similarities, never identification probabilities.
