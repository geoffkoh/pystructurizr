"""Headless smoke tests for the pystructurizr NiceGUI viewer."""

from __future__ import annotations

from pathlib import Path

import pytest
from nicegui import ui
from nicegui.testing import User

from pystructurizr.viewer.app import _build_tree_nodes, _load_workspace
from pystructurizr.viewer.cytoscape_view import apply_positions, to_cytoscape_elements


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def _setup_workspace(tmp_path: Path) -> Path:
    folder = tmp_path / "ws"
    folder.mkdir()
    (folder / "workspace.dsl").write_text((FIXTURE_DIR / "example.dsl").read_text())
    return folder


# ---------------------------------------------------------------------------
# Pure-Python helpers — fast, no NiceGUI runtime needed
# ---------------------------------------------------------------------------


def test_load_workspace_reports_missing_folder() -> None:
    ws, msg = _load_workspace("")
    assert ws is None
    assert "folder" in msg.lower()


def test_load_workspace_reports_missing_dsl(tmp_path: Path) -> None:
    ws, msg = _load_workspace(str(tmp_path))
    assert ws is None
    assert "workspace.dsl" in msg


def test_load_workspace_parses_fixture(tmp_path: Path) -> None:
    folder = _setup_workspace(tmp_path)
    ws, msg = _load_workspace(str(folder))
    assert ws is not None
    assert "Internet Banking" in msg
    assert len(ws.people) == 1
    assert len(ws.software_systems) == 3


def test_tree_nodes_for_fixture(tmp_path: Path) -> None:
    folder = _setup_workspace(tmp_path)
    ws, _ = _load_workspace(str(folder))
    assert ws is not None
    nodes = _build_tree_nodes(ws)
    labels = {n["label"] for n in nodes}
    assert any(label.startswith("People") for label in labels)
    assert any(label.startswith("Software Systems") for label in labels)
    assert any(label.startswith("Views") for label in labels)


def test_apply_positions_round_trip(tmp_path: Path) -> None:
    folder = _setup_workspace(tmp_path)
    ws, _ = _load_workspace(str(folder))
    assert ws is not None
    view = ws.views[0]
    apply_positions(view, {"customer": (100, 200), "bank": (300, 400)})
    assert len(view.element_views) == 2
    elements = to_cytoscape_elements(ws, view)
    positioned = {e["data"]["id"]: e["position"] for e in elements if "position" in e}
    assert positioned["customer"] == {"x": 100, "y": 200}
    assert positioned["bank"] == {"x": 300, "y": 400}


# ---------------------------------------------------------------------------
# End-to-end smoke via nicegui.testing.User
# ---------------------------------------------------------------------------


pytestmark = [
    pytest.mark.nicegui_main_file("src/pystructurizr/viewer/app.py"),
]


async def test_page_renders_initial_state(user: User) -> None:
    await user.open("/")
    await user.should_see("pystructurizr viewer")
    await user.should_see("Load a workspace to begin")


async def test_load_populates_tree(user: User, tmp_path: Path) -> None:
    folder = _setup_workspace(tmp_path)
    await user.open("/")
    user.find(kind=ui.input).type(str(folder))
    user.find("Load").click()
    await user.should_see("Personal Banking Customer")
    await user.should_see("Internet Banking System")


async def test_select_view_renders_canvas(user: User, tmp_path: Path) -> None:
    folder = _setup_workspace(tmp_path)
    await user.open("/")
    user.find(kind=ui.input).type(str(folder))
    user.find("Load").click()
    await user.should_see("SystemContext")
