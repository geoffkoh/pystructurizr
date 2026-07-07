"""Integration tests for the webapp FastAPI backend."""

from __future__ import annotations

import os
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


def test_files_hides_include_fragments(root: Path) -> None:
    split = Path(__file__).parent.parent / "fixtures" / "split_workspace"
    shutil.copytree(split, root / "split_workspace")
    client = TestClient(create_app(root=root))
    files = client.get("/api/files").json()
    assert "split_workspace/workspace.dsl" in files
    # Fragment files without a workspace block are not offered for loading.
    assert not any("model/" in f for f in files)


def test_load_split_workspace_resolves_includes(root: Path) -> None:
    split = Path(__file__).parent.parent / "fixtures" / "split_workspace"
    shutil.copytree(split, root / "split_workspace")
    client = TestClient(create_app(root=root))
    response = client.post("/api/load", json={"path": "split_workspace/workspace.dsl"})
    assert response.status_code == 200
    assert response.json()["name"] == "Split Workspace"


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
    assert set(node["data"]) == {
        "label",
        "kind",
        "color",
        "technology",
        "description",
        "tags",
    }


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


def _touch_future(path: Path, offset_ns: int = 10_000_000_000) -> None:
    """Bump a file's mtime far enough that the watch token must change."""
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + offset_ns))


def test_status_before_load_is_empty(client: TestClient) -> None:
    body = client.get("/api/status").json()
    assert body == {"path": None, "generation": 0, "error": None}


def test_status_reloads_when_source_changes(client: TestClient, root: Path) -> None:
    _load(client)
    assert client.get("/api/status").json()["generation"] == 0

    source = root / "example.dsl"
    source.write_text(
        source.read_text(encoding="utf-8").replace(
            '"Internet Banking"', '"Renamed Banking"'
        ),
        encoding="utf-8",
    )
    _touch_future(source)

    body = client.get("/api/status").json()
    assert body["generation"] == 1
    assert body["error"] is None
    assert client.get("/api/workspace").json()["name"] == "Renamed Banking"


def test_status_reloads_when_include_fragment_changes(root: Path) -> None:
    split = Path(__file__).parent.parent / "fixtures" / "split_workspace"
    shutil.copytree(split, root / "split_workspace")
    client = TestClient(create_app(root=root))
    response = client.post("/api/load", json={"path": "split_workspace/workspace.dsl"})
    assert response.status_code == 200

    fragment = root / "split_workspace" / "model" / "people.dsl"
    fragment.write_text('user = person "Renamed User"\n', encoding="utf-8")
    _touch_future(fragment)

    body = client.get("/api/status").json()
    assert body["generation"] == 1
    workspace = client.get("/api/workspace").json()
    assert workspace["model"]["people"][0]["name"] == "Renamed User"


def test_status_keeps_old_workspace_on_parse_error(
    client: TestClient, root: Path
) -> None:
    _load(client)
    source = root / "example.dsl"
    source.write_text("workspace", encoding="utf-8")  # missing { -> ParseError
    _touch_future(source)

    body = client.get("/api/status").json()
    assert body["generation"] == 0
    assert body["error"] is not None
    # The previously loaded workspace is still served.
    assert client.get("/api/workspace").json()["name"] == "Internet Banking"


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
