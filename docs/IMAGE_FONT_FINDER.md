# Image Font Finder guide

The image and all processing stay on your computer. Scores describe relative geometry, not the probability of finding the original font.

## Main workflow

1. Open **Image Font Finder**. Drop an image or choose **Browse / replace image**. PNG, JPEG, BMP, TIFF and WebP are accepted by actual contents, up to 20 MiB, 20 megapixels and 10,000 pixels per side. EXIF orientation is applied; only the first frame/page is used.
2. Drag around one complete line in one typeface, leaving a little background. **Pan image**, Zoom and **Fit image** help inspect the source. Numeric crop bounds under Advanced settings provide a keyboard alternative.
3. Enter **Exact text shown in image (case-sensitive)**, including all capitalization, numbers, spaces, punctuation and repeated characters. `Supreme!` and `SUPREME!` are different. The app never recognizes, corrects, case-converts or Unicode-normalizes the text. One line and up to 160 characters are supported; tabs, newlines and control characters are rejected with a message.
4. Inspect **Letter geometry** and **Corrected original**. Adjust processing if needed, then click **Find Matching Fonts**. Both an image and valid visible text are required.
5. Review candidates and choose **Inspect match**. More distinctive lettering helps separate nearly identical faces. All eligible fonts in the shared catalog are screened before shortlist refinement.

Changing text does not require reuploading the image. Changing text, geometry, processing or matching settings removes old rankings and cancels obsolete work. Each result labels the exact text used. Zoom and pan affect only the editing view.

## Geometry controls

**Rotate 90°** corrects sideways images. Fine rotation adjusts up to 30 degrees in either direction. Optional automatic deskew applies a conservative projection-based estimate; inspect the result. Leave margin around letters because rotation cannot recover clipped source pixels.

**Perspective corners** initializes four handles around the crop. Drag them in top-left, top-right, bottom-right, bottom-left order around a flat lettering plane. Crossing or degenerate corners are rejected. **Reset crop** removes perspective correction. **Restore original** resets the current upload's image geometry and processing defaults; the user's source file is never modified. Curved or artistically warped lettering may require a better reference.

## Processing controls

| Control | Purpose |
|---|---|
| Polarity | Auto, dark letters, or light letters |
| Automatic | Otsu threshold or useful alpha coverage for transparent sources |
| Manual threshold | Direct threshold control |
| Adaptive threshold | Local background variation; inspect for amplified textures |
| Selected fill color | Use the color control or click inside a letter with **Pick foreground color**; adjust tolerance |
| Transparency | Use alpha coverage; rejects images without useful transparency |
| Contrast | Adjust separation before thresholding |
| Noise reduction | Conservative removal of tiny components; disable for delicate punctuation |
| Outline handling | Preserve ink, retain an alternative color core, or prefer the core |
| Shadow suppression | Prefer a separately colored fill core; warns if one cannot be isolated |
| Background removal | Exclude transparent pixels; white transparent lettering gets a dark viewing background |

The pipeline does not remove outlines with fixed erosion or fill counters. Automatic outline/shadow isolation is heuristic. Use manual fill-color selection for multistroke outlines, glows or complex backgrounds. Same-color attached shadows may remain inseparable. Useful base/core alternatives are retained for matching.

## Matching and results

FreeType and HarfBuzz shape/render the exact string, including kerning and supported Unicode shaping. Missing glyphs and native render failures are excluded and counted. No browser screenshots are used for scoring.

Strict sensitivity preserves proportions closely; Balanced allows modest artwork changes; Flexible allows wider but bounded correction. Base character spacing is measured in pixels at a nominal 96-pixel render size. Nearby tracking values are evaluated. Refine 30, 60 (default), or 120 shortlisted faces. Named variable instances can be sampled; continuous axis optimization is not performed.

The first 20 results appear initially; **Show 20 more results** reveals more. Filter by the shared favorites or declared categories. Diagnostics expose overlap, contours, structural similarity, projection agreement and character evidence when segmentation is reliable. Repeated letters have balanced per-character influence. Connected or uncertain lettering uses whole-word evidence.

## Comparison and integration

- **Side by side:** corrected reference left, fitted candidate right.
- **Overlay:** cyan candidate over the original or processed reference.
- **Difference:** pale shared ink, red reference-only ink, cyan candidate-only ink.
- **Outline:** candidate contours over the reference.

Adjust X/Y position, overall/horizontal/vertical scale, rotation, spacing and opacity. Adjustments only affect the visual comparison; automated ranks/scores stay unchanged. **Auto Align** recalculates bounded alignment at the current spacing. **Reset Alignment** restores the original automated fit. **Export PNG** downloads the current comparison with a visible qualification that it is not proof of identity.

Results reuse **Favorite**, **Details**, **Copy name** and **Locate file**. **Add to comparison** adds the catalog face and sets the Font Browser preview to the exact reference text. **Open in Font Browser** searches its full name. No second favorites database or font scan exists.

## Privacy, lifetime and performance

Generated IDs store originals temporarily in `data/matching-temp/`; working images are downsampled to at most 2048 pixels on the longest side. At most six uploads, six processed references and six jobs are retained in the running service. Cleanup expires temporary content after approximately an hour, including old files from previous runs. Restarting or refreshing does not restore editing sessions; upload again. Persistent Font Browser settings/favorites remain independent.

One background matching worker runs at a time. Cancellation occurs between native operations; the current operation must finish. Caches are bounded. A full 639-face development search took about 18 seconds; runtime varies with hardware, text, formats and shortlist size.

## Troubleshooting and limits

- Unrelated results: verify the exact text and case, crop one line/typeface, and inspect the mask. The app cannot infer a transcription mismatch; uncertain character boundaries only produce guidance.
- Missing dots/punctuation: lower noise removal or adjust threshold/color tolerance.
- Outlines/shadows dominate: select the interior fill color manually. Attached effects of the same color may require a cleaner image.
- Similar scores: inspect more distinctive letters, counters and terminals. Different binaries or metrically similar faces can be visually indistinguishable.
- No eligible fonts: check missing-glyph counts and add compatible local fonts.
- Expired image/job or changed catalog: upload/process/search again.
- Complex scripts: single-direction runs are shaped; full mixed-direction paragraph layout, vertical/multiline text, fallback and all color/bitmap formats are not supported. Unsupported faces are excluded.
- Distressed, modified, tiny, curved or heavily photographed lettering needs further real-artwork validation. Synthetic benchmark accuracy is not a real-world guarantee.

No OCR, telemetry, cloud services, models or system-wide image tools are added. Native FreeType/HarfBuzz/OpenCV dependencies remain local and packageable; a later Windows x64 distribution must include their native libraries and review their licenses. No executable is produced here.
