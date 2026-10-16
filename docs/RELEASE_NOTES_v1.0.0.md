# FontFinderLocal v1.0.0

The first portable Windows release combines a local Font Browser with an Image Font Finder. No account, installation or internet connection is required for normal use.

## Highlights

- Browse installed and custom-folder fonts, preview your own text, save favorites, explore variable fonts and compare up to 12 faces.
- Upload a lettering image, crop and process it, and rank matching candidates from your local font collection.
- Enter the reference text manually, exactly as shown, including case and punctuation. **No OCR or automatic text correction is performed.**
- Inspect side-by-side, overlay, difference and outline comparisons with alignment controls and PNG export.
- Portable Windows x64 package with embedded runtime, local settings persistence and clean shutdown.

## Download and launch

Download `FontFinderLocal-1.0.0-Windows-x64-portable.zip` and extract the entire archive into a writable folder. Run `Start-FontFinderLocal.bat` or `FontFinderLocal.exe`. Keep `_internal` beside the executable. Python is not required.

Stop with `Stop-FontFinderLocal.bat` or Ctrl+C in the console. Closing the browser tab alone does not stop the application. The `.sha256` attachment allows you to verify the archive with PowerShell `Get-FileHash -Algorithm SHA256`.

## Compatibility and limitations

Validated on Windows 11 x64. Windows 10 x64 is an intended but independently unverified target. This release has not yet been tested on a second clean Windows machine. The executable is unsigned.

Matching scores represent relative shape similarity, not identification certainty. Results depend on the fonts installed, image quality and supplied text. Some unsupported or missing-glyph faces are excluded. No proprietary font files are included.

## License

MIT; bundled third-party dependencies retain their own license notices.
