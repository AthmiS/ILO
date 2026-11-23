import os
import tempfile
import pytest
from app import create_app

@pytest.fixture
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "DATABASE": path, "DISABLE_CSRF": True})
    yield app
    try: os.unlink(path)
    except OSError: pass

@pytest.fixture
def client(app):
    return app.test_client()
