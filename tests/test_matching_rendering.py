"""Native-renderer identity, variable geometry and cache regression checks."""
from pathlib import Path

import numpy as np
import pytest
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, TTCollection
from fontTools.varLib import build

from app.config import Config
from app.discovery import Catalog
from app.persistence import Store
from app.matching.raster import Rasterizer, RenderError
from app.rendering import FontUnavailable
from conftest import make_font


def catalog_for(tmp_path, monkeypatch, paths):
    monkeypatch.setattr("app.discovery.system_sources",lambda issue:iter(paths))
    catalog=Catalog(Store(tmp_path/"data"));catalog.start();catalog.worker.join(10)
    assert not catalog.worker.is_alive()
    return catalog.snapshot()["fonts"]


def change_glyph(path, height=1200):
    with TTFont(path) as font:
        pen=TTGlyphPen(None)
        pen.moveTo((100,-300));pen.lineTo((100,height));pen.lineTo((450,height));pen.lineTo((450,-300));pen.closePath()
        font["glyf"]["A"]=pen.glyph();font.save(path)


def test_matching_uses_collection_face_geometry(tmp_path,monkeypatch):
    a=make_font(tmp_path/"a.ttf",family="Triangle")
    b=make_font(tmp_path/"b.ttf",family="Rectangle")
    change_glyph(b)
    collection=TTCollection();collection.fonts=[TTFont(a),TTFont(b)]
    path=tmp_path/"faces.ttc";collection.save(path);collection.close()
    faces=sorted(catalog_for(tmp_path,monkeypatch,[path]),key=lambda f:f["face_index"])
    assert [f["face_index"] for f in faces]==[0,1]
    raster=Rasterizer();one=raster.render(faces[0],"A");two=raster.render(faces[1],"A")
    assert two.mask.shape[0]>one.mask.shape[0]*2
    assert np.count_nonzero(two.mask)/two.mask.size>.9
    assert np.count_nonzero(one.mask)/one.mask.size<.6


def test_variable_coordinates_change_native_bounds_and_cache(tmp_path,monkeypatch):
    # Two compatible masters with actual gvar data, not fvar metadata alone.
    a=make_font(tmp_path/"normal.ttf");b=make_font(tmp_path/"tall.ttf")
    with TTFont(b) as font:
        glyph=font["glyf"]["A"]
        glyph.coordinates[1]=(300,2200)
        font.save(b)
    design=DesignSpaceDocument();axis=AxisDescriptor()
    axis.name="Weight";axis.tag="wght";axis.minimum=400;axis.default=400;axis.maximum=900;design.addAxis(axis)
    for path,weight in ((a,400),(b,900)):
        source=SourceDescriptor();source.path=str(path);source.name=str(weight);source.location={"Weight":weight};design.addSource(source)
    variable,_,_=build(design);path=tmp_path/"variable.ttf";variable.save(path);variable.close()
    face=catalog_for(tmp_path,monkeypatch,[path])[0];raster=Rasterizer()
    normal=raster.render(face,"A S",coordinates={"wght":400})
    tall=raster.render(face,"A S",coordinates={"wght":900})
    assert tall.mask.shape[0]>normal.mask.shape[0]*2
    assert raster.render(face,"A S",coordinates={"wght":400}) is normal
    assert raster.render(face,"A S",coordinates={"wght":900}) is tall
    with pytest.raises(RenderError):raster.render(face,"A S",coordinates={"wght":901})


def test_native_cache_keys_and_unavailable_file(client):
    face=client.app.state.catalog.snapshot()["fonts"][0]
    raster=client.app.state.matching.rasterizer
    normal=raster.render(face,"A S A")
    assert raster.render(face,"A S A") is normal
    spaced=raster.render(face," A  S A ")
    tracked=raster.render(face,"A S A",tracking=2)
    larger=raster.render(face,"A S A",size=126)
    assert spaced.text==" A  S A " and spaced.advance>normal.advance
    assert tracked.advance>normal.advance and larger.mask.shape[0]>normal.mask.shape[0]
    with pytest.raises(RenderError):raster.render(face,"a S A")
    # Cached pixels must not conceal replacement of the underlying catalog file.
    path=Path(face["path"]);path.write_bytes(path.read_bytes()+b"changed")
    with pytest.raises(FontUnavailable):raster.render(face,"A S A")
