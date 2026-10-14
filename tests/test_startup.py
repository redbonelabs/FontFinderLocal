import socket
import pytest
from app.config import Config, APP_ROOT
from app.startup import InstanceLock, bind_socket, running_instance


def test_configuration_is_portable_and_local(tmp_path, monkeypatch):
    monkeypatch.setenv("FONTFINDER_DATA_DIR", str(tmp_path / "portable-data"))
    config = Config.load(); config.prepare()
    assert config.data_dir == tmp_path / "portable-data"
    assert config.port == 8766 and config.host == "127.0.0.1"
    assert (APP_ROOT / "frontend/index.html").is_file()
    with pytest.raises(ValueError): Config(tmp_path, host="0.0.0.0")
    with pytest.raises(ValueError): Config(tmp_path, port=70000)


def test_busy_port_uses_another_loopback_port():
    first = bind_socket(0)
    try:
        second = bind_socket(first.getsockname()[1])
        try:
            assert second.getsockname()[0] == "127.0.0.1"
            assert second.getsockname()[1] != first.getsockname()[1]
        finally: second.close()
    finally: first.close()


def test_single_instance_lock_and_release(tmp_path):
    first = InstanceLock(tmp_path / "lock")
    assert first.acquire()
    second = InstanceLock(tmp_path / "lock")
    try:
        assert not second.acquire()
        first.close()
        assert second.acquire()
    finally:
        if not first.file.closed: first.close()
        second.close()


def test_stale_instance_is_ignored(tmp_path):
    state = tmp_path / "server.json"
    assert running_instance(state) is None
    state.write_text('{"port": -1}')
    assert running_instance(state) is None
