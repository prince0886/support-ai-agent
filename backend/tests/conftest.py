from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def settings(tmp_path) -> Settings:
    database_file = tmp_path / "supportpilot-test.db"
    return Settings(
        database_url=f"sqlite:///{database_file.as_posix()}",
        llm_enabled=False,
        seed_on_startup=True,
    )


@pytest.fixture()
def client(settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client