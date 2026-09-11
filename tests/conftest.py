from ninjarmy.core import model
import pytest

@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Point global STATE_PATH at a temp directory."""
    dir = tmp_path / ".ninjarmy"
    dir.mkdir()
    monkeypatch.setattr(model, "STATE_PATH", dir)
    return dir
