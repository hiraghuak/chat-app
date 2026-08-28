import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    os.environ.pop("OPENROUTER_API_KEY", None)
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def set_key():
    """Set/clear the API key for a test and refresh the cached settings."""
    from app.config import get_settings

    def _set(value):
        if value is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = value
        get_settings.cache_clear()

    yield _set
    os.environ.pop("OPENROUTER_API_KEY", None)
    get_settings.cache_clear()
