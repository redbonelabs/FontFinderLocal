"""Isolated browser regression fixture; never reads/writes the user's preferences.

Run: python -m tests.preview_layout_server, open /preview-layout-check.
Uses the actual application frontend and native font loader, with known glyph ink
outside the nominal font metrics. The variable fixture grows A from 0.7 to 2.2 em.
"""
import json
import os
from pathlib import Path
import uvicorn
from fastapi.responses import FileResponse
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.varLib import build
from tests.conftest import make_font
from app.config import Config
from app.api import create_app
from app.startup import bind_socket
from app import discovery


def main():
    root=Path('test-results/preview-layout').resolve();root.mkdir(parents=True,exist_ok=True)
    regular=make_font(root/'regular.ttf',family='Preview Regular')
    tall=make_font(root/'tall.ttf',family='Preview Tall')
    with TTFont(tall) as font:
        pen=TTGlyphPen(None)
        pen.moveTo((-350,-800));pen.lineTo((300,2200));pen.lineTo((1100,-800));pen.closePath()
        font['glyf']['A']=pen.glyph();font['hmtx']['A']=(600,-350)
        font.save(tall)
    design=DesignSpaceDocument()
    axis=AxisDescriptor();axis.name='Weight';axis.tag='wght';axis.minimum=400;axis.default=400;axis.maximum=900
    design.addAxis(axis)
    for path,weight in [(regular,400),(tall,900)]:
        source=SourceDescriptor();source.path=str(path);source.name=str(weight);source.location={'Weight':weight}
        source.familyName='Preview Variable';source.styleName='Regular';design.addSource(source)
    variable,_,_=build(design)
    variable['name'].setName('Preview Variable',1,3,1,0x409)
    variable['name'].setName('Preview Variable',16,3,1,0x409)
    variable.save(root/'variable.ttf')
    discovery.system_sources=lambda issue: iter([regular,tall,root/'variable.ttf'])
    sock=bind_socket(8767);port=sock.getsockname()[1]
    app=create_app(Config(root/'data'),shutdown=lambda:setattr(server,'should_exit',True))
    @app.get('/preview-layout-check')
    def page():return FileResponse(Path(__file__).with_name('preview_layout.html'))
    @app.get('/preview-layout-check.js')
    def script():return FileResponse(Path(__file__).with_name('preview_layout.js'),media_type='text/javascript')
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,access_log=False))
    (root/'server.json').write_text(json.dumps({'port':port,'pid':os.getpid()}))
    print(f'Preview regression fixture: http://127.0.0.1:{port}/preview-layout-check',flush=True)
    server.run(sockets=[sock])


if __name__=='__main__':main()
