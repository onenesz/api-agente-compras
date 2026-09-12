import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def cases():
    return json.loads((Path(__file__).resolve().parents[1] / "tests_data/expected_cases.json").read_text())


@pytest.fixture(scope="session")
def data(cases):
    return cases["datos_referencia"]


@pytest.fixture
def client():
    with TestClient(app) as client:
        assert isinstance(client, httpx.Client)
        yield client
