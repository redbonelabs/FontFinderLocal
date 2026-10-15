"""Build and archive a self-contained local Windows x64 distribution."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        raise SystemExit('Build using 64-bit Python on Windows.')
    bundle=ROOT/'dist/FontFinderLocal'
    if (bundle/'data').exists():
        raise SystemExit('Move your runtime data out of dist before rebuilding; refusing to overwrite user data.')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm',
                    '--distpath', str(ROOT/'dist'), '--workpath', str(ROOT/'build'),
                    str(ROOT/'packaging/FontFinderLocal.spec')], cwd=ROOT, check=True)
    bundle=ROOT/'dist/FontFinderLocal'
    if (bundle/'data').exists():
        raise SystemExit('Refusing to package a bundle with runtime user data.')
    shutil.copyfile(ROOT/'packaging/PORTABLE_README.txt',bundle/'README.txt')
    for name,args in [('Start',''),('Stop',' --stop')]:
        (bundle/f'{name}-FontFinderLocal.bat').write_text(
            '@echo off\n"%~dp0FontFinderLocal.exe"'+args+'\nif errorlevel 1 pause\n',encoding='utf-8')
    licenses=bundle/'licenses';licenses.mkdir(exist_ok=True)
    packages={}
    # Preserve installed distribution notices, including bundled native-library
    # notices carried in wheels. Build-only tools are identified in the inventory.
    for dist in metadata.distributions():
        name=dist.metadata['Name'];packages[name]=dist.version
        for file in dist.files or []:
            if file.name.upper().startswith(('LICENSE','COPYING','NOTICE')) or file.name.upper().endswith(('.LICENSE','.NOTICE')):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    destination=licenses/name/str(file).replace('..','_').replace(':','_')
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(source,destination)
    python_license=Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.exists():shutil.copyfile(python_license,licenses/'PYTHON-LICENSE.txt')
    revision=subprocess.check_output(['git','-c',f'safe.directory={ROOT.as_posix()}','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    info={'application':'FontFinderLocal','platform':'Windows x64','python':platform.python_version(),
          'source_checkpoint':revision,'build_environment_packages':dict(sorted(packages.items())),
          'bundle':'PyInstaller onedir; native runtime in _internal; no Python installation required'}
    (bundle/'BUILD_INFO.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    release=ROOT/'releases';release.mkdir(exist_ok=True)
    archive=release/'FontFinderLocal-Windows-x64-portable.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():output.write(path,path.relative_to(bundle.parent))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n',encoding='ascii')
    summary={'executable':str(bundle/'FontFinderLocal.exe'),'zip':str(archive),'zip_bytes':archive.stat().st_size,
             'unpacked_bytes':sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file()),'sha256':digest}
    (release/'build-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
