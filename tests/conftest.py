from pathlib import Path
import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, TTCollection, newTable
from fontTools.ttLib.tables._f_v_a_r import Axis, NamedInstance
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Config


def make_font(path, family="Test Français 日本", style="Regular", weight=400, variable=False, italic=False):
    builder = FontBuilder(1000, isTTF=True)
    glyphs = [".notdef", "space", "A", "S"]
    builder.setupGlyphOrder(glyphs)
    builder.setupCharacterMap({32: "space", 65: "A", 83: "S"})
    outlines = {}
    for glyph in glyphs:
        pen = TTGlyphPen(None)
        if glyph != "space":
            pen.moveTo((100, 0)); pen.lineTo((300, 700)); pen.lineTo((500, 0)); pen.closePath()
        outlines[glyph] = pen.glyph()
    builder.setupGlyf(outlines)
    builder.setupHorizontalMetrics({g: (600, 0) for g in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": family, "styleName": style,
                           "fullName": f"{family} {style}", "psName": "TestFace-" + style.replace(" ", "")})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200,
                    usWeightClass=weight, sFamilyClass=8 << 8, fsSelection=1 if italic else 0)
    builder.setupPost(italicAngle=-12 if italic else 0)
    builder.setupMaxp()
    if variable:
        table = newTable("fvar")
        axis = Axis(); axis.axisTag = "wght"; axis.minValue = 100; axis.defaultValue = 400; axis.maxValue = 900; axis.flags = 0; axis.axisNameID = 256
        instance = NamedInstance(); instance.subfamilyNameID = 257; instance.flags = 0; instance.coordinates = {"wght": 700}; instance.postscriptNameID = 0xFFFF
        table.axes = [axis]; table.instances = [instance]
        builder.font["fvar"] = table
        builder.font["name"].setName("Weight", 256, 3, 1, 0x409)
        builder.font["name"].setName("Bold instance", 257, 3, 1, 0x409)
    builder.save(path)
    return path


@pytest.fixture
def font_dir(tmp_path):
    folder = tmp_path / "fonts"; folder.mkdir()
    make_font(folder / "regular.ttf")
    make_font(folder / "bold.ttf", style="Bold", weight=700)
    return folder


@pytest.fixture
def client(tmp_path, font_dir, monkeypatch):
    monkeypatch.setattr("app.discovery.system_sources", lambda issue: iter(font_dir.glob("*.ttf")))
    app = create_app(Config(tmp_path / "data"))
    with TestClient(app, base_url="http://127.0.0.1:8766") as client:
        app.state.catalog.worker.join(10)
        client.headers["X-FontFinder-Token"] = app.state.token
        yield client
