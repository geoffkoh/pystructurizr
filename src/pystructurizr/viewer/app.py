"""NiceGUI viewer for pystructurizr workspaces.

The viewer is a single-page NiceGUI app that loads a workspace.dsl from a
folder, displays its element hierarchy in a side tree, and renders the
selected view in the main canvas. Implemented in milestones M1–M7 (see
docs/prompts/nicegui_app.prompt.md).

This module exposes `main()`. Run with `uv run python -m pystructurizr.viewer.app`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from nicegui import ui

from pystructurizr.models import Workspace
from pystructurizr.parser.dsl import ParseError, parse_dsl_file


@dataclass
class ViewerState:
    """Module-level singleton holding the loaded workspace and UI handles."""

    workspace: Optional[Workspace] = None
    folder_path: str = ""


_state = ViewerState()


def _load_workspace(folder: str) -> tuple[Optional[Workspace], str]:
    """Resolve workspace.dsl under folder and parse it.

    Returns (workspace, message). On success workspace is set; on failure
    workspace is None and message describes what went wrong.
    """
    folder = folder.strip()
    if not folder:
        return None, "Please enter a folder path."
    dsl_path = Path(folder).expanduser() / "workspace.dsl"
    if not dsl_path.is_file():
        return None, f"No workspace.dsl in {dsl_path.parent}"
    try:
        workspace = parse_dsl_file(dsl_path)
    except ParseError as exc:
        return None, f"DSL parse error: {exc}"
    except OSError as exc:
        return None, f"Could not read {dsl_path}: {exc}"
    return workspace, f"Loaded {workspace.name or '(unnamed workspace)'}"


def _on_load_clicked() -> None:
    workspace, message = _load_workspace(_state.folder_path)
    if workspace is None:
        ui.notify(message, type="negative")
        return
    _state.workspace = workspace
    ui.notify(message, type="positive")


@ui.page("/")
def index() -> None:
    with ui.header(elevated=True).classes("items-center"):
        ui.label("pystructurizr viewer").classes("text-h6")

    with ui.splitter(value=28).classes("w-full") as splitter:
        with splitter.before:
            with ui.column().classes("p-4 gap-3 w-full"):
                ui.label("Workspace").classes("text-subtitle1 text-weight-medium")
                ui.input(
                    label="Folder containing workspace.dsl",
                    placeholder="/path/to/workspace",
                ).bind_value(_state, "folder_path").classes("w-full")
                ui.button("Load", on_click=_on_load_clicked).props("color=primary")
                ui.separator()
                ui.tree([], label_key="label", node_key="id").classes("w-full")
        with splitter.after:
            with ui.column().classes("p-8 w-full items-center justify-center"):
                ui.label("Load a workspace to begin").classes("text-lg text-grey-7")


def main() -> None:
    """Start the NiceGUI server."""
    ui.run(title="pystructurizr viewer", reload=False, show=False, port=8765)


if __name__ in {"__main__", "__mp_main__"}:
    main()
