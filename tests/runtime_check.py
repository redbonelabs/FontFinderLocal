"""Read-only live API checks. Run with the launcher already running."""
from io import BytesIO
import json
from pathlib import Path
from urllib.request import urlopen, Request

from fontTools.ttLib import TTFont
from app.config import Config


def main():
    state = json.loads((Config.load().data_dir / "server.json").read_text())
    base = f"http://127.0.0.1:{state['port']}"
    def get(path):
        with urlopen(base + path, timeout=30) as response:
            return response.read()
    assert json.loads(get("/api/health"))["application"] == "FontFinderLocal"
    assert b"FontFinderLocal" in get("/")
    catalog = json.loads(get("/api/fonts"))
    assert not catalog["scan"]["running"]
    assert catalog["fonts"]
    samples = {}
    for face in catalog["fonts"]:
        for key, condition in [("ttf", face["container"] == "TTF"), ("collection", face["container"] == "TTC"),
                               ("cff", face["format"] == "OpenType/CFF"), ("variable", bool(face["axes"]))]:
            if condition and key not in samples:
                samples[key] = face
    results = []
    for kind, face in samples.items():
        data = get(f"/api/fonts/{face['id']}/asset")
        with TTFont(BytesIO(data)) as font:
            assert len(font.getGlyphOrder()) > 0
            if kind == "variable": assert "fvar" in font
            if kind == "collection": assert data[:4] != b"ttcf"
        details = json.loads(get(f"/api/fonts/{face['id']}"))
        assert details["id"] == face["id"]
        results.append({"kind": kind, "font": face["full_name"], "bytes": len(data), "face_index": face["face_index"]})
    report = {"base_url": base, "faces": len(catalog["fonts"]),
              "families": len({f["family"] for f in catalog["fonts"]}),
              "scan": catalog["scan"], "actual_assets": results}
    output = Path("test-results/runtime-api.json"); output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
