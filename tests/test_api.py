from fastapi.testclient import TestClient
from app.api import create_app
from app.config import Config
from app.persistence import Store


def test_health_frontend_and_catalog(client):
    assert client.get("/api/health").json()["application"] == "FontFinderLocal"
    assert client.get("/api/health").json()["version"] == "1.0.0"
    response = client.get("/")
    assert response.status_code == 200 and "FontFinderLocal" in response.text
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/static/app.js").status_code == 200
    fonts = client.get("/api/fonts").json()["fonts"]
    assert len(fonts) == 2
    font = fonts[0]
    assert client.get(f"/api/fonts/{font['id']}").json()["full_name"] == font["full_name"]
    response = client.get(f"/api/fonts/{font['id']}/asset")
    assert response.content[:4] == b"\x00\x01\x00\x00"
    assert response.headers["content-type"] == "font/ttf"


def test_origin_csrf_and_host_protection(client):
    assert client.post("/api/rescan", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/rescan", headers={"X-FontFinder-Token": "bad"}).status_code == 403
    assert client.get("/api/bootstrap", headers={"Host": "evil.example"}).status_code == 403
    assert client.get("/api/fonts", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert client.get("/api/bootstrap", headers={"Origin": "null"}).status_code == 403
    assert client.post("/api/rescan", headers={"Origin": "http://127.0.0.1:8766"}).status_code == 200
    client.app.state.catalog.worker.join(10)


def test_font_endpoint_cannot_serve_arbitrary_paths(client):
    for identifier in ["C:%5CWindows%5Cwin.ini", "not-a-font", "a" * 64 + "-0", "..%5Csecret"]:
        assert client.get(f"/api/fonts/{identifier}/asset").status_code == 404
        assert client.post(f"/api/fonts/{identifier}/open-folder").status_code == 404
    assert client.get("/static/..%2Fapp%2Fconfig.py").status_code == 404


def test_exact_settings_and_favorites_survive_recreation(client, tmp_path):
    font_id = client.get("/api/fonts").json()["fonts"][0]["id"]
    settings = client.get("/api/bootstrap").json()["settings"]
    settings.update(text='  Héllo, "WORLD"!\n日本  ', size=83, density="compact", query="Bold", compare=[font_id])
    assert client.put("/api/settings", json=settings).status_code == 200
    assert client.put(f"/api/favorites/{font_id}", json={"enabled": True}).status_code == 200
    other = create_app(Config(tmp_path / "data"), scan_on_start=False)
    with TestClient(other, base_url="http://127.0.0.1") as reopened:
        boot = reopened.get("/api/bootstrap").json()
        assert boot["settings"] == settings
        assert boot["favorites"] == [font_id]
    assert client.put(f"/api/favorites/{font_id}", json={"enabled": False}).json()["favorites"] == []


def test_settings_validation(client):
    for body in [{"size": 999}, {"density": "invented"}, {"compare": ["C:/secret"]}, {"text": "x" * 10001}, {"unexpected": 1}]:
        assert client.put("/api/settings", json=body).status_code == 422


def test_custom_directories_persist_deduplicate_and_remove(client, font_dir):
    added = client.post("/api/directories", json={"path": str(font_dir), "recursive": False})
    assert added.status_code == 200
    client.app.state.catalog.worker.join(10)
    directories = added.json()["directories"]
    assert Store(client.app.state.store.path.parent).get("directories", []) == directories
    assert client.post("/api/directories", json={"path": str(font_dir / ".")}).status_code == 409
    fonts = client.get("/api/fonts").json()["fonts"]
    assert all(f["sources"] == ["custom", "installed"] for f in fonts)
    assert client.post("/api/directories", json={"path": "relative"}).status_code == 422
    assert client.delete("/api/directories/missing").status_code == 404
    assert client.delete(f"/api/directories/{directories[0]['id']}").json()["directories"] == []
    client.app.state.catalog.worker.join(10)
    assert all(f["sources"] == ["installed"] for f in client.get("/api/fonts").json()["fonts"])


def test_open_folder_is_catalog_scoped(client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.api.subprocess.Popen", lambda args, **kwargs: calls.append((args, kwargs)))
    import os
    font = client.get("/api/fonts").json()["fonts"][0]
    response = client.post(f"/api/fonts/{font['id']}/open-folder", json={"path": "C:/arbitrary"})
    if os.name == "nt":
        assert response.status_code == 200 and calls[0][0][-1] == font["path"]
        assert calls[0][1]["shell"] is False
    else:
        assert response.status_code == 400
