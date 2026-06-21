"""NiceGUI viewer for pystructurizr workspaces.

The viewer is a single-page NiceGUI app that loads a workspace.dsl from a
folder, displays its element hierarchy in a side tree, and renders the
selected view in the main canvas. Implemented in milestones M1–M7 (see
docs/prompts/nicegui_app.prompt.md).

This module exposes `main()`. Run with `uv run python -m pystructurizr.viewer.app`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from nicegui import ui

from pystructurizr.generators.mermaid import MermaidGenerator
from pystructurizr.models import DeploymentNode, View, Workspace
from pystructurizr.parser.dsl import ParseError, parse_dsl_file
from pystructurizr.viewer.cytoscape_view import (
    DEFAULT_STYLESHEET,
    apply_positions,
    to_cytoscape_elements,
)


TreeNode = dict[str, Any]

CYTOSCAPE_CDN = (
    '<script src="https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"'
    ' integrity="sha384-IWROdLKRsN1UuJywMlWl7/blXQ8GEooN2n7dzTxfEPd7ybYIKCUJ2Ol/1Gpf3YV4"'
    ' crossorigin="anonymous"></script>'
)


@dataclass
class ViewerState:
    """Module-level singleton holding the loaded workspace and UI handles."""

    workspace: Optional[Workspace] = None
    folder_path: str = ""
    current_view_key: Optional[str] = None
    mermaid_cache: dict[str, str] = field(default_factory=dict)
    canvas_mode: str = "Mermaid"  # 'Mermaid' or 'Cytoscape'


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
    if not node_id or not node_id.startswith("view:"):
        return
    _state.current_view_key = node_id[len("view:"):]
    _render_canvas.refresh()


def _current_view() -> Optional[View]:
    if _state.workspace is None or _state.current_view_key is None:
        return None
    for v in _state.workspace.views:
        if v.key == _state.current_view_key:
            return v
    return None


def _workspace_json_path() -> Optional[Path]:
    if not _state.folder_path:
        return None
    return Path(_state.folder_path).expanduser() / "workspace.json"


def _draw_cytoscape() -> None:
    """Push the current view's elements into the browser Cytoscape instance.

    Honors any pre-positioned nodes (preset layout) and resets the
    in-browser cyPositions buffer so subsequent drags accumulate fresh.
    """
    view = _current_view()
    if view is None or _state.workspace is None:
        return
    elements = to_cytoscape_elements(_state.workspace, view)
    has_preset = any("position" in el for el in elements)
    layout = "{ name: 'preset' }" if has_preset else "{ name: 'cose', animate: false, padding: 30 }"
    js = f"""
    (function() {{
      if (typeof cytoscape === 'undefined') {{ return; }}
      var container = document.getElementById('cy-canvas');
      if (!container) {{ return; }}
      if (window._cy_instance) {{ window._cy_instance.destroy(); }}
      window.cyPositions = {{}};
      window._cy_instance = cytoscape({{
        container: container,
        elements: {json.dumps(elements)},
        style: {json.dumps(DEFAULT_STYLESHEET)},
        layout: {layout},
        wheelSensitivity: 0.2,
      }});
      window._cy_instance.on('dragfree', 'node', function(evt) {{
        var n = evt.target;
        window.cyPositions[n.id()] = {{
          x: Math.round(n.position('x')),
          y: Math.round(n.position('y')),
        }};
      }});
    }})();
    """
    ui.run_javascript(js)


def _workspace_to_dict(ws: Workspace) -> dict[str, Any]:
    """Serialize Workspace to a JSON-safe dict via dataclasses.asdict.

    All pystructurizr enums extend `str`, so they round-trip natively
    through json.dumps without a custom encoder.
    """
    return asdict(ws)


async def _on_save_clicked() -> None:
    """Harvest drag positions from the browser and write workspace.json."""
    if _state.workspace is None:
        ui.notify("No workspace loaded.", type="warning")
        return
    target = _workspace_json_path()
    if target is None:
        ui.notify("Workspace folder unknown — reload first.", type="warning")
        return
    view = _current_view()
    if view is not None and _state.canvas_mode == "Cytoscape":
        try:
            raw = await ui.run_javascript("return window.cyPositions || {};", timeout=3.0)
        except TimeoutError:
            raw = {}
        if isinstance(raw, dict) and raw:
            positions: dict[str, tuple[int, int]] = {
                str(k): (int(v["x"]), int(v["y"]))
                for k, v in raw.items()
                if isinstance(v, dict) and "x" in v and "y" in v
            }
            if positions:
                apply_positions(view, positions)
    try:
        target.write_text(json.dumps(_workspace_to_dict(_state.workspace), indent=2))
    except OSError as exc:
        ui.notify(f"Could not write {target}: {exc}", type="negative")
        return
    ui.notify(f"Saved {target}", type="positive")


@ui.refreshable
def _render_canvas() -> None:
    if _state.workspace is None:
        ui.label("Load a workspace to begin").classes("text-lg text-grey-7")
        return
    if _state.current_view_key is None:
        ui.label("Select a view from the tree").classes("text-lg text-grey-7")
        return

    with ui.row().classes("items-center w-full q-mb-md gap-4"):
        ui.label(f"View: {_state.current_view_key}").classes("text-subtitle1")
        ui.toggle(
            ["Mermaid", "Cytoscape"],
            value=_state.canvas_mode,
            on_change=_on_canvas_mode_change,
        ).props("dense")
        ui.space()
        ui.button("Save", icon="save", on_click=_on_save_clicked).props("flat color=primary")

    if _state.canvas_mode == "Mermaid":
        if not _state.mermaid_cache:
            _state.mermaid_cache = MermaidGenerator(_state.workspace).generate_all()
        diagram = _state.mermaid_cache.get(_state.current_view_key)
        if diagram is None:
            ui.label(f"No Mermaid diagram for view {_state.current_view_key!r}").classes("text-grey-7")
            return
        ui.mermaid(diagram).classes("w-full")
    else:
        ui.html(
            '<div id="cy-canvas" style="width:100%; height:600px; border:1px solid #ddd; background:#fafafa;"></div>'
        )
        ui.timer(0.05, _draw_cytoscape, once=True)


def _on_canvas_mode_change(event: Any) -> None:
    _state.canvas_mode = event.value
    _render_canvas.refresh()


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
    _state.current_view_key = None
    _state.mermaid_cache = {}
    ui.notify(message, type="positive")
    _render_tree.refresh()
    _render_canvas.refresh()


@ui.page("/")
def index() -> None:
    ui.add_head_html(CYTOSCAPE_CDN)
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
            with ui.column().classes("p-6 w-full"):
                _render_canvas()


def main() -> None:
    """Start the NiceGUI server.

    Binds to localhost only — the viewer has no authentication, so we
    do not expose it on other interfaces. Override by editing this line
    if you genuinely need to share the viewer (and add auth first).
    """
    ui.run(title="pystructurizr viewer", reload=False, show=False, host="127.0.0.1", port=8765)


if __name__ in {"__main__", "__mp_main__"}:
    main()
