import shutil
from io import BytesIO
from fontTools.ttLib import TTFont, TTCollection

from app.discovery import Catalog, validate_directory, walk_fonts
from app.metadata import extract_metadata
from app.persistence import Store
from app.rendering import Renderer, FontUnavailable
from conftest import make_font
import pytest


def test_unicode_metadata_and_distinct_styles(font_dir):
    regular = extract_metadata(font_dir / "regular.ttf")[0]
    bold = extract_metadata(font_dir / "bold.ttf")[0]
    assert regular["family"] == "Test Français 日本"
    assert regular["weight"] == 400 and bold["weight"] == 700
    assert regular["category"] == "sans-serif"
    assert regular["postscript_name"] == "TestFace-Regular"
    assert regular["coverage"] == [[32, 32], [65, 65], [83, 83]]


def test_variable_axes_and_instances(tmp_path):
    face = extract_metadata(make_font(tmp_path / "variable.ttf", variable=True))[0]
    assert face["axes"] == [{"tag": "wght", "name": "Weight", "min": 100, "default": 400, "max": 900}]
    assert face["instances"][0]["coordinates"] == {"wght": 700}


def test_italic_and_unknown_category(tmp_path):
    path = make_font(tmp_path / "italic.ttf", italic=True)
    with TTFont(path) as font:
        font["OS/2"].sFamilyClass = 0; font.save(path)
    face = extract_metadata(path)[0]
    assert face["italic"] and face["category"] == "unknown"


def test_collection_indices_and_standalone_assets(tmp_path, font_dir, monkeypatch):
    collection = TTCollection()
    collection.fonts = [TTFont(font_dir / "regular.ttf"), TTFont(font_dir / "bold.ttf")]
    path = tmp_path / "faces.ttc"; collection.save(path); collection.close()
    assert [f["face_index"] for f in extract_metadata(path)] == [0, 1]
    monkeypatch.setattr("app.discovery.system_sources", lambda issue: iter([path]))
    catalog = Catalog(Store(tmp_path / "data")); catalog.start(); catalog.worker.join(10)
    faces = catalog.snapshot()["fonts"]
    assert len(faces) == 2 and len({f["id"] for f in faces}) == 2
    for face in faces:
        data = Renderer().asset(face)
        assert data[:4] == b"\x00\x01\x00\x00"
        font = TTFont(BytesIO(data))
        assert font["OS/2"].usWeightClass == face["weight"]
        font.close()


def test_duplicate_files_not_distinct_faces_and_cache(tmp_path, font_dir, monkeypatch):
    copied = tmp_path / "copy.ttf"; shutil.copyfile(font_dir / "regular.ttf", copied)
    broken = tmp_path / "broken.otf"; broken.write_bytes(b"invalid")
    monkeypatch.setattr("app.discovery.system_sources", lambda issue: iter([*font_dir.glob("*.ttf"), copied, broken]))
    catalog = Catalog(Store(tmp_path / "data")); catalog.start(); catalog.worker.join(10)
    first = catalog.snapshot()
    assert len(first["fonts"]) == 2
    assert sorted(len(f["locations"]) for f in first["fonts"]) == [1, 2]
    assert len(first["scan"]["issues"]) == 1
    ids = {f["id"] for f in first["fonts"]}
    monkeypatch.setattr("app.discovery.extract_metadata", lambda path: (_ for _ in ()).throw(AssertionError("Cache not used")))
    catalog.start(); catalog.worker.join(10)
    assert catalog.snapshot()["scan"]["cached"] == 3
    assert {f["id"] for f in catalog.snapshot()["fonts"]} == ids


def test_different_files_same_family_stay_separate(tmp_path, monkeypatch):
    a = make_font(tmp_path / "one.ttf")
    b = make_font(tmp_path / "two.ttf", weight=500)
    monkeypatch.setattr("app.discovery.system_sources", lambda issue: iter([a, b]))
    catalog = Catalog(Store(tmp_path / "data")); catalog.start(); catalog.worker.join(10)
    assert len(catalog.snapshot()["fonts"]) == 2


def test_changed_file_is_not_served(client, font_dir):
    face = client.get("/api/fonts").json()["fonts"][0]
    assert client.get(f"/api/fonts/{face['id']}/asset").status_code == 200
    from pathlib import Path
    Path(face["path"]).write_bytes(b"changed")
    assert client.get(f"/api/fonts/{face['id']}/asset").status_code == 409


def test_recursive_scan_and_directory_validation(tmp_path, font_dir):
    nested = font_dir / "nested"; nested.mkdir(); make_font(nested / "other.ttf")
    assert len(list(walk_fonts(font_dir, False, lambda *args: None))) == 2
    assert len(list(walk_fonts(font_dir, True, lambda *args: None))) == 3
    assert validate_directory(str(font_dir)) == font_dir.resolve()
    for invalid in ["", "relative/path", str(tmp_path / "absent"), str(font_dir / "regular.ttf"), "\\\\server\\share", "x\x00y"]:
        with pytest.raises(ValueError): validate_directory(invalid)


def test_woff_asset_conversion(tmp_path, monkeypatch):
    path = make_font(tmp_path / "source.ttf")
    woff = tmp_path / "compressed.woff2"
    with TTFont(path) as font:
        font.flavor = "woff2"; font.save(woff)
    monkeypatch.setattr("app.discovery.system_sources", lambda issue: iter([woff]))
    catalog = Catalog(Store(tmp_path / "data")); catalog.start(); catalog.worker.join(10)
    face = catalog.snapshot()["fonts"][0]
    assert Renderer().asset(face)[:4] == b"\x00\x01\x00\x00"


def test_variable_asset_retains_axes(tmp_path, monkeypatch):
    path = make_font(tmp_path / "variable.ttf", variable=True)
    monkeypatch.setattr("app.discovery.system_sources", lambda issue: iter([path]))
    catalog = Catalog(Store(tmp_path / "data")); catalog.start(); catalog.worker.join(10)
    with TTFont(BytesIO(Renderer().asset(catalog.snapshot()["fonts"][0]))) as font:
        assert font["fvar"].axes[0].axisTag == "wght"
        assert font["fvar"].instances[0].coordinates == {"wght": 700}


def test_opentype_cff_metadata_and_asset(tmp_path, monkeypatch):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.t2CharStringPen import T2CharStringPen
    builder = FontBuilder(1000, isTTF=False)
    glyphs = [".notdef", "A"]
    builder.setupGlyphOrder(glyphs); builder.setupCharacterMap({65: "A"})
    outlines = {}
    for glyph in glyphs:
        pen = T2CharStringPen(600, None)
        pen.moveTo((100, 0)); pen.lineTo((300, 700)); pen.lineTo((500, 0)); pen.closePath()
        outlines[glyph] = pen.getCharString()
    builder.setupCFF("TestCFF", {"FullName": "Test CFF", "FamilyName": "Test CFF", "Weight": "Regular"}, outlines, {})
    builder.setupHorizontalMetrics({g: (600, 0) for g in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": "Test CFF", "styleName": "Regular", "fullName": "Test CFF", "psName": "TestCFF"})
    builder.setupOS2(); builder.setupPost(); builder.setupMaxp()
    path = tmp_path / "test.otf"; builder.save(path)
    monkeypatch.setattr("app.discovery.system_sources", lambda issue: iter([path]))
    catalog = Catalog(Store(tmp_path / "data")); catalog.start(); catalog.worker.join(10)
    face = catalog.snapshot()["fonts"][0]
    assert face["format"] == "OpenType/CFF"
    with TTFont(BytesIO(Renderer().asset(face))) as font:
        assert "CFF " in font
