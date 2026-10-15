# Portable package build and validation

Use 64-bit Python 3.13 on Windows. From the repository root, prepare a virtual environment with the protected runtime lock and packaging tools:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.venv\Scripts\python.exe -m pip install -r packaging/requirements-build.txt
.venv\Scripts\python.exe packaging/build_portable.py
```

The builder creates `dist/FontFinderLocal` and the ZIP/checksum/build summary under `releases`. It refuses to rebuild if `dist/FontFinderLocal/data` exists: move your saved data to a safe location first. Validate an extracted copy instead of launching the pristine distribution folder. Build outputs are intentionally excluded from Git. BUILD_INFO records the application source checkpoint and installed build environment inventory; that inventory is not a claim that every build dependency is bundled.

Run the existing regressions and the external-executable validator:

```powershell
.venv\Scripts\python.exe -m pytest -q --basetemp=test-results/step4-regression
node --test tests/test_preview_rows.mjs
.venv\Scripts\python.exe packaging/validate_portable.py
```

The validator uses existing `test-results/ground-truth/00-scale.png` from prior validation, plus installed Windows fonts (including CFF, variable and TTC examples). Preserve these prerequisites; this is a host integration check, not a generic empty-machine test. It creates its own external extraction, custom test fonts and saved settings, starts only that copy, and stops it afterward. Development Python drives HTTP assertions; the tested EXE uses its own embedded runtime. Detailed output is saved under test-results. See STEP4_PROGRESS.md for the exact released hash and completed results.

End users need neither Python nor these build tools. Extract the whole ZIP and launch Start-FontFinderLocal.bat. Read PORTABLE_README.txt for portable data and shutdown behavior.
