# Windows x64 onedir bundle. Keep frontend and native libraries inside _internal.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

root = Path(SPECPATH).parent
hidden = collect_submodules('fontTools.ttLib.tables') + [
    'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio',
    'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan.on',
    'fontTools.encodings.codecs', 'fontTools.unicodedata',
]
a = Analysis(
    [str(root / 'packaging' / 'launcher.py')],
    pathex=[str(root)],
    binaries=collect_dynamic_libs('freetype'),
    datas=[(str(root / 'frontend'), 'frontend')] + collect_data_files('fontTools'),
    hiddenimports=hidden,
    excludes=['pytest', 'IPython', 'tkinter', 'matplotlib'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='FontFinderLocal',
          debug=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='FontFinderLocal')
