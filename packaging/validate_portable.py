"""Exercise the delivered ZIP as an external, independently launched application.

The development Python is only the test driver; the child EXE has a sanitized
environment, external CWD, its own database, and no access via Python search paths.
"""
import ctypes
import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from tests.conftest import make_font


def module_paths(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x410,False,pid)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    try:
        modules=(ctypes.c_void_p*2048)();needed=ctypes.c_ulong()
        psapi.EnumProcessModulesEx.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.c_ulong]
        assert psapi.EnumProcessModulesEx(handle,modules,ctypes.sizeof(modules),ctypes.byref(needed),3)
        psapi.GetModuleFileNameExW.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_ulong]
        paths=[]
        for item in modules[:needed.value//ctypes.sizeof(ctypes.c_void_p)]:
            name=ctypes.create_unicode_buffer(32768)
            if psapi.GetModuleFileNameExW(handle,item,name,len(name)):paths.append(name.value)
        return paths
    finally:kernel.CloseHandle(handle)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,default=ROOT/'releases/FontFinderLocal-1.0.0-Windows-x64-portable.zip')
    parser.add_argument('--report',type=Path,default=ROOT/'test-results/release-1.0.0-portable-validation.json')
    args=parser.parse_args()
    archive=args.archive.resolve()
    root=Path(tempfile.mkdtemp(prefix='FontFinderLocal-Step4-'))
    extracted=root/'Extracted package Å';extracted.mkdir()
    cwd=root/'Unrelated working directory';cwd.mkdir()
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(name.startswith('FontFinderLocal/data/') or name.endswith(('.ttf','.otf','.ttc','.woff','.woff2')) for name in z.namelist()),'Unexpected user data/fonts in release'
        z.extractall(extracted)
    bundle=extracted/'FontFinderLocal';exe=bundle/'FontFinderLocal.exe'
    assert (bundle/'LICENSE.txt').read_bytes()==(ROOT/'LICENSE').read_bytes()
    assert json.loads((bundle/'BUILD_INFO.json').read_text())['version']=='1.0.0'
    data=bundle/'data';assert not data.exists()
    binary=exe.read_bytes();pe=struct.unpack_from('<I',binary,0x3c)[0]
    assert binary[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',binary,pe+4)[0]==0x8664
    env=os.environ.copy()
    for key in list(env):
        if key.upper().startswith(('PYTHON','VIRTUAL_ENV','FONTFINDER_')):env.pop(key)
    env['PATH']=str(Path(os.environ['SYSTEMROOT'])/'System32')
    busy=socket.socket();busy.bind(('127.0.0.1',0));busy.listen(1)
    occupied=busy.getsockname()[1]
    logfile=(root/'portable-console.log').open('ab')
    report={'zip':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'external_root':str(root),'executable':str(exe),'cwd':str(cwd),'pe_machine':'AMD64',
            'environment':'PATH=Windows System32; no Python, venv or FontFinder environment overrides',
            'checks':[]}
    process=None;base='';token=''
    def save():
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2),encoding='utf-8')
    def checked(name):report['checks'].append(name);save();print(name,flush=True)
    def api(path,body=None,method=None,raw=False,binary=False):
        content=body if raw else None if body is None else json.dumps(body).encode()
        request=Request(base+path,data=content,method=method,headers={'X-FontFinder-Token':token,'Content-Type':'application/octet-stream' if raw else 'application/json'})
        with urlopen(request,timeout=30) as response:return response.read() if binary else json.load(response)
    def start():
        nonlocal process,base,token
        process=subprocess.Popen([str(exe),'--no-browser','--port',str(occupied)],cwd=cwd,env=env,
                                 stdout=logfile,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            if process.poll() is not None:raise RuntimeError(f'EXE exited {process.returncode}; see {root}/portable-console.log')
            try:
                state=json.loads((data/'server.json').read_text());base=f"http://127.0.0.1:{state['port']}";token=state['token']
                boot=api('/api/bootstrap')
                assert api('/api/health')['version']=='1.0.0'
                assert boot['token']==token and state['port']!=occupied
                report['port']=state['port'];report['pid']=state['pid'];return boot
            except (OSError,ValueError,KeyError):time.sleep(.2)
        raise TimeoutError('Startup did not become healthy')
    def catalog():
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            value=api('/api/fonts')
            if not value['scan']['running']:return value
            time.sleep(.3)
        raise TimeoutError('Catalog scan')
    def job_done(key):
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            job=api('/api/matching/jobs/'+key)
            if job['status'] in ('completed','failed','cancelled'):return job
            time.sleep(.2)
        raise TimeoutError('Matching job')
    try:
        boot=start();checked('External x64 executable launches with port fallback and portable data')
        duplicate=subprocess.run([str(exe),'--no-browser'],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        assert duplicate.returncode==0 and b'already running' in duplicate.stdout
        checked('Second launch reuses the same instance')
        for path in (ROOT/'frontend').iterdir():
            if path.is_file():assert api('/static/'+path.name,binary=True)==path.read_bytes(),path.name
        assert b'FontFinderLocal' in api('/',binary=True)
        checked('Complete bundled HTML/CSS/JavaScript matches protected frontend byte-for-byte')
        library=catalog();assert library['fonts'];report['installed_faces']=len(library['fonts']);report['scan_issues']=library['scan']['issues']
        kinds={}
        for face in library['fonts']:
            for kind,condition in [('TTF',face['container']=='TTF'),('TTC',face['container']=='TTC'),('CFF',face['format']=='OpenType/CFF'),('variable',bool(face['axes']))]:
                if condition and kind not in kinds:
                    asset=api(f"/api/fonts/{face['id']}/asset",binary=True)
                    with TTFont(BytesIO(asset)) as font:assert len(font.getGlyphOrder())>0
                    kinds[kind]=face['full_name']
        report['assets']=kinds;assert {'TTF','TTC','CFF','variable'}<=kinds.keys()
        checked('Installed Windows discovery and TTF/CFF/TTC/variable browser assets')
        custom=root/'Custom fonts';custom.mkdir()
        fixture=make_font(custom/'portable.ttf',family='Portable Folder Fixture')
        for flavor in ['woff','woff2']:
            with TTFont(fixture) as font:font.flavor=flavor;font.save(custom/f'portable.{flavor}')
        api('/api/directories',{'path':str(custom),'recursive':True})
        library=catalog();custom_faces=[f for f in library['fonts'] if f['family']=='Portable Folder Fixture']
        assert len(custom_faces)==3 and all('custom' in f['sources'] for f in custom_faces)
        for face in custom_faces:
            with TTFont(BytesIO(api(f"/api/fonts/{face['id']}/asset",binary=True))) as font:assert 'glyf' in font
        checked('Custom-folder TTF/WOFF/WOFF2 discovery and decompression')
        # Generate a neutral test image in memory; no private reference image or
        # previously generated development artifact is needed in a fresh clone.
        sample_font=ImageFont.truetype(str(Path(os.environ['SYSTEMROOT'])/'Fonts/arialbd.ttf'),100)
        bounds=sample_font.getbbox('Supreme!')
        sample=Image.new('RGB',(bounds[2]-bounds[0]+40,bounds[3]-bounds[1]+40),'white')
        ImageDraw.Draw(sample).text((20-bounds[0],20-bounds[1]),'Supreme!',font=sample_font,fill='black')
        encoded=BytesIO();sample.save(encoded,format='PNG')
        image=api('/api/matching/images',encoded.getvalue(),raw=True)
        processed=api('/api/matching/process',{'image_id':image['id']})
        text='  Supreme!  '
        job=api('/api/matching/jobs',{'process_id':processed['id'],'text':text})
        result=job_done(job['id']);assert result['status']=='completed' and result['text']==text and result['results'],result
        report['matching']={k:result[k] for k in ('seconds','catalog_faces','eligible','excluded')}
        selected=result['results'][0]['font_id']
        assert api(f"/api/matching/jobs/{job['id']}/preview/{selected}",binary=True).startswith(b'\x89PNG')
        for mode in ['side','overlay','difference','outline']:
            png=api(f"/api/matching/jobs/{job['id']}/compare",{'font_id':selected,'alignment':{'mode':mode,'x':2,'y':-1,'rotation':1,'tracking':2,'scale_x':.97}},binary=True)
            assert Image.open(BytesIO(png)).width>=620
        auto=api(f"/api/matching/jobs/{job['id']}/auto-align",{'font_id':selected,'alignment':{'tracking':2}});assert auto['tracking']==2
        cancel=api('/api/matching/jobs',{'process_id':processed['id'],'text':'Supreme!'})
        api(f"/api/matching/jobs/{cancel['id']}/cancel",{})
        assert job_done(cancel['id'])['status']=='cancelled'
        checked('Frozen native matching, exact whitespace/text, previews, four comparisons, auto-align and cancellation')
        paths=module_paths(report['pid']);report['loaded_modules']=paths
        assert not any(str(ROOT).lower() in p.lower() for p in paths)
        assert any('python313.dll' in p.lower() and str(extracted).lower() in p.lower() for p in paths)
        checked('Loaded native modules do not come from development tree; bundled Python DLL confirmed')
        settings=boot['settings'];settings.update(text='Portable\nÅgj',size=46,query='Portable Folder Fixture')
        api('/api/settings',settings,'PUT');api(f'/api/favorites/{selected}',{'enabled':True},'PUT')
        stop=subprocess.run([str(exe),'--stop'],cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        assert stop.returncode==0;assert process.wait(timeout=30)==0;assert not (data/'server.json').exists()
        checked('Portable --stop shuts down cleanly and removes live server state')
        restarted=start();assert restarted['settings']==settings and selected in restarted['favorites']
        assert restarted['directories'][0]['path']==str(custom)
        assert any(f['family']=='Portable Folder Fixture' for f in catalog()['fonts'])
        checked('Settings, favorites and custom folders survive restart')
        api('/api/shutdown',{},'POST');assert process.wait(timeout=30)==0;assert not (data/'server.json').exists()
        checked('Authenticated shutdown after restart releases process and state')
        report['passed']=True;save()
    except Exception as exc:
        report['passed']=False;report['error']=str(exc);save();raise
    finally:
        if process and process.poll() is None:
            try:api('/api/shutdown',{},'POST');process.wait(timeout=15)
            except Exception:process.terminate();process.wait(timeout=10)
        busy.close();logfile.close()
        print('Validation artifacts:',root,flush=True)


if __name__=='__main__':main()
