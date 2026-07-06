"""Adapt pystructurizr views into React Flow-shaped graph data.

The heavy lifting (deciding which elements are visible and collecting the
relationships between them) lives in
:mod:`pystructurizr.webapp.g6_view`. This module re-shapes that graph output
into the node/edge structure the React Flow frontend expects.
"""

from __future__ import annotations

from typing import Any

from pystructurizr.models import View, ViewType, Workspace
from pystructurizr.webapp.g6_view import KIND_COLOURS, to_g6_data


ReactFlowNode = dict[str, Any]
ReactFlowEdge = dict[str, Any]
ReactFlowData = dict[str, list[Any]]


_SUPPORTED_TYPES = frozenset(
    {
        ViewType.SYSTEM_CONTEXT,
        ViewType.CONTAINER,
        ViewType.COMPONENT,
        ViewType.DEPLOYMENT,
    }
)


def is_supported(view: View) -> bool:
    """Return whether a view type produces a meaningful React Flow graph.

    Args:
        view: The view to check.

    Returns:
        ``True`` for ``systemContext``, ``container``, ``component`` and
        ``deployment`` views; ``False`` otherwise.
    """
    return view.type in _SUPPORTED_TYPES


def view_graph(
    workspace: Workspace, view: View, expand: set[str] | None = None
) -> ReactFlowData:
    """Build React Flow ``{nodes, edges}`` data for ``view``.

    Node ``data`` carries everything the graph builder emitted (label, kind,
    technology, description, tags, boundary/expansion flags) plus the kind's
    palette ``color``. Nodes nested inside a boundary group node carry a
    top-level ``parentId``. A ``position`` is included only when the
    underlying view element has stored coordinates; otherwise it is omitted
    so the frontend can run its own auto-layout.

    Args:
        workspace: The workspace the view belongs to.
        view: The view to render.
        expand: For container views, ids of containers to expand in place.

    Returns:
        A dict with ``nodes`` and ``edges`` lists in React Flow shape.
    """
    g6 = to_g6_data(workspace, view, expand)

    nodes: list[ReactFlowNode] = []
    for g6_node in g6["nodes"]:
        data = dict(g6_node.get("data", {}))
        data["color"] = KIND_COLOURS.get(data.get("kind", ""))
        node: ReactFlowNode = {"id": g6_node["id"], "data": data}
        if "parentId" in g6_node:
            node["parentId"] = g6_node["parentId"]
        style = g6_node.get("style")
        if style is not None and "x" in style and "y" in style:
            node["position"] = {"x": style["x"], "y": style["y"]}
        nodes.append(node)

    edges: list[ReactFlowEdge] = []
    for g6_edge in g6["edges"]:
        edges.append(
            {
                "id": g6_edge["id"],
                "source": g6_edge["source"],
                "target": g6_edge["target"],
                "label": g6_edge.get("data", {}).get("label", ""),
            }
        )

    return {"nodes": nodes, "edges": edges}
