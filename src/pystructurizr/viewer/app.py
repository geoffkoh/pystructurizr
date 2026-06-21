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
from typing import Any, Optional

from nicegui import ui

from pystructurizr.models import DeploymentNode, Workspace
from pystructurizr.parser.dsl import ParseError, parse_dsl_file


TreeNode = dict[str, Any]


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


def _deployment_node_to_tree(dn: DeploymentNode) -> TreeNode:
    children: list[TreeNode] = [_deployment_node_to_tree(c) for c in dn.children]
    children.extend({"id": f"el:{i.id}", "label": f"[infra] {i.name}"} for i in dn.infrastructure_nodes)
    children.extend(
        {"id": f"el:{i.id}", "label": f"[ss-inst] {i.software_system_id}"}
        for i in dn.software_system_instances
    )
    children.extend(
        {"id": f"el:{i.id}", "label": f"[c-inst] {i.container_id}"}
        for i in dn.container_instances
    )
    node: TreeNode = {"id": f"el:{dn.id}", "label": dn.name}
    if children:
        node["children"] = children
    return node


def _build_tree_nodes(ws: Workspace) -> list[TreeNode]:
    """Translate a Workspace into NiceGUI tree-node dicts.

    Element ids are prefixed `el:` and view keys `view:` so click handlers
    can dispatch by type.
    """
    nodes: list[TreeNode] = []
    if ws.people:
        nodes.append({
            "id": "group:people",
            "label": f"People ({len(ws.people)})",
            "children": [{"id": f"el:{p.id}", "label": p.name} for p in ws.people],
        })
    if ws.software_systems:
        sys_children: list[TreeNode] = []
        for system in ws.software_systems:
            system_node: TreeNode = {"id": f"el:{system.id}", "label": system.name}
            container_children: list[TreeNode] = []
            for container in system.containers:
                container_node: TreeNode = {"id": f"el:{container.id}", "label": container.name}
                if container.components:
                    container_node["children"] = [
                        {"id": f"el:{comp.id}", "label": comp.name} for comp in container.components
                    ]
                container_children.append(container_node)
            if container_children:
                system_node["children"] = container_children
            sys_children.append(system_node)
        nodes.append({
            "id": "group:systems",
            "label": f"Software Systems ({len(ws.software_systems)})",
            "children": sys_children,
        })
    if ws.deployment_nodes:
        nodes.append({
            "id": "group:deployment",
            "label": f"Deployment Nodes ({len(ws.deployment_nodes)})",
            "children": [_deployment_node_to_tree(dn) for dn in ws.deployment_nodes],
        })
    all_views = ws.views.get_all_views()
    if all_views:
        nodes.append({
            "id": "group:views",
            "label": f"Views ({len(all_views)})",
            "children": [
                {"id": f"view:{v.key}", "label": v.key or v.title or v.type.value}
                for v in all_views
            ],
        })
    return nodes


def _on_node_selected(node_id: Optional[str]) -> None:
    """Dispatch tree node clicks. View rendering is wired in M4."""
    if not node_id:
        return
    if node_id.startswith("view:"):
        ui.notify(f"Selected view {node_id[5:]} (rendering in M4)", type="info")


@ui.refreshable
def _render_tree() -> None:
    nodes = _build_tree_nodes(_state.workspace) if _state.workspace else []
    if not nodes:
        ui.label("No workspace loaded.").classes("text-grey-7")
        return
    ui.tree(nodes, label_key="label", node_key="id", on_select=lambda e: _on_node_selected(e.value)).classes("w-full")


def _on_load_clicked() -> None:
    workspace, message = _load_workspace(_state.folder_path)
    if workspace is None:
        ui.notify(message, type="negative")
        return
    _state.workspace = workspace
    ui.notify(message, type="positive")
    _render_tree.refresh()


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
                _render_tree()
        with splitter.after:
            with ui.column().classes("p-8 w-full items-center justify-center"):
                ui.label("Load a workspace to begin").classes("text-lg text-grey-7")


def main() -> None:
    """Start the NiceGUI server."""
    ui.run(title="pystructurizr viewer", reload=False, show=False, port=8765)


if __name__ in {"__main__", "__mp_main__"}:
    main()
