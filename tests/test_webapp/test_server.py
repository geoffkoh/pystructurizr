"""Integration tests for the webapp FastAPI backend."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pystructurizr.webapp.server import create_app

FIXTURE = Path(__file__).parent.parent / "fixtures" / "example.dsl"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Return a source root containing a copy of the example fixture."""
    shutil.copy(FIXTURE, tmp_path / "example.dsl")
    return tmp_path


@pytest.fixture
def client(root: Path) -> TestClient:
    """Return a TestClient for an app rooted at the fixture directory."""
    return TestClient(create_app(root=root))


def _load(client: TestClient) -> None:
    """Load the example workspace via the API."""
    response = client.post("/api/load", json={"path": "example.dsl"})
    assert response.status_code == 200


def test_files_lists_fixture(client: TestClient) -> None:
    response = client.get("/api/files")
    assert response.status_code == 200
    assert "example.dsl" in response.json()


def test_load_then_workspace_has_software_systems(client: TestClient) -> None:
    _load(client)
    response = client.get("/api/workspace")
    assert response.status_code == 200
    data = response.json()
    assert data["model"]["software_systems"]


def test_load_returns_views_index(client: TestClient) -> None:
    response = client.post("/api/load", json={"path": "example.dsl"})
    body = response.json()
    assert body["name"] == "Internet Banking"
    assert body["path"] == "example.dsl"
    assert any(v["key"] == "SystemContext" for v in body["views"])


def test_views_marks_system_context_supported(client: TestClient) -> None:
    _load(client)
    response = client.get("/api/views")
    assert response.status_code == 200
    views = {v["key"]: v for v in response.json()}
    assert views["SystemContext"]["type"] == "systemContext"
    assert views["SystemContext"]["supported"] is True


def test_view_graph_has_nodes_and_edges(client: TestClient) -> None:
    _load(client)
    response = client.get("/api/views/SystemContext/graph")
    assert response.status_code == 200
    data = response.json()
    assert data["nodes"]
    assert data["edges"]
    node = data["nodes"][0]
    assert set(node["data"]) == {"label", "kind", "color"}


def test_unknown_view_key_returns_404(client: TestClient) -> None:
    _load(client)
    response = client.get("/api/views/does-not-exist/graph")
    assert response.status_code == 404


def test_workspace_before_load_returns_409(client: TestClient) -> None:
    response = client.get("/api/workspace")
    assert response.status_code == 409


def test_path_traversal_rejected(client: TestClient) -> None:
    response = client.post("/api/load", json={"path": "../../etc/passwd"})
    assert response.status_code == 400


def test_no_static_dir_serves_not_built_hint(root: Path, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    client = TestClient(create_app(root=root, static_dir=missing))
    response = client.get("/")
    assert response.status_code == 200
    assert "not built" in response.json()["detail"]


def test_built_static_dir_serves_index(root: Path, tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        "<!doctype html><title>spa</title>", encoding="utf-8"
    )
    client = TestClient(create_app(root=root, static_dir=static_dir))
    response = client.get("/")
    assert response.status_code == 200
    assert "<title>spa</title>" in response.text
