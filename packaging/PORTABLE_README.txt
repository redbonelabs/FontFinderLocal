FontFinderLocal — Portable Windows x64

1. Extract the entire ZIP to a writable local folder.
2. Double-click Start-FontFinderLocal.bat (or FontFinderLocal.exe).
3. Your default browser opens the local application. Keep its console open.
4. Stop with Stop-FontFinderLocal.bat, or Ctrl+C in the application console.

Python, pip and the development project are NOT required. Keep the _internal
folder beside FontFinderLocal.exe; the EXE alone is not the distribution.
All frontend assets and matching libraries are included. No installed fonts,
user reference images, developer database or saved preferences are bundled.

Settings, favorites, font catalog and logs are created in data beside the EXE.
Keep that data folder when moving/updating the application. Saved custom font
paths must still exist on the destination PC; rescan after moving computers.
For a clean start, stop the app and move data aside as a backup.

The app binds only to 127.0.0.1, normally port 8766. If occupied, it prints and
opens another local port. A second launch of the same copy reuses its instance.
The browser needs access to localhost; no CDN or remote matching service is used.
Image Font Finder requires an image AND the exact manually entered text. No OCR.

Command-line options: --no-browser, --port NUMBER, --stop.
Advanced: FONTFINDER_DATA_DIR overrides the normal portable data location.

Troubleshooting:
- Extract first; do not run directly inside the ZIP preview.
- Use a writable folder, not Program Files or another protected location.
- If startup fails, launch through Start-FontFinderLocal.bat to retain the error,
  and inspect data/fontfinder.log if created.
- Refresh the browser after restarting. Rescan if fonts have changed.
- This build is unsigned; Windows may display a publisher/reputation warning.
  The SHA256 file beside the release ZIP identifies the exact delivered archive.

Validated on the development Windows x64 host from an independently extracted
folder with Python/development environment variables removed. A pristine Windows
VM without developer software has not been tested. No installer or admin rights
are intentionally required. See BUILD_INFO.json and licenses for component details.
