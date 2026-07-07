"""Adapt pystructurizr views into React Flow-shaped graph data.

The heavy lifting (deciding which elements are visible and collecting the
relationships between them) lives in
:mod:`pystructurizr.webapp.g6_view`. This module re-shapes that graph output
into the node/edge structure the React Flow frontend expects.
"""

from __future__ import annotations

from typing import Any

from pystructurizr.models import RankDirection, View, ViewType, Workspace
from pystructurizr.webapp.g6_view import KIND_COLOURS, to_g6_data


# View rank direction → dagre rankdir.
_RANK_DIRECTIONS: dict[RankDirection, str] = {
    RankDirection.TOP_BOTTOM: "TB",
    RankDirection.BOTTOM_TOP: "BT",
    RankDirection.LEFT_RIGHT: "LR",
    RankDirection.RIGHT_LEFT: "RL",
}


ReactFlowNode = dict[str, Any]
ReactFlowEdge = dict[str, Any]
ReactFlowData = dict[str, Any]


_SUPPORTED_TYPES = frozenset(
    {
        ViewType.SYSTEM_LANDSCAPE,
        ViewType.SYSTEM_CONTEXT,
        ViewType.CONTAINER,
        ViewType.COMPONENT,
        ViewType.DYNAMIC,
        ViewType.DEPLOYMENT,
    }
)


def is_supported(view: View) -> bool:
    """Return whether a view type produces a meaningful React Flow graph.

    Args:
        view: The view to check.

    Returns:
        ``True`` for ``systemLandscape``, ``systemContext``, ``container``,
        ``component``, ``dynamic`` and ``deployment`` views; ``False``
        otherwise.
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
        # Tag-based style backgrounds win over the built-in kind palette.
        data["color"] = data.get("background") or KIND_COLOURS.get(data.get("kind", ""))
        node: ReactFlowNode = {"id": g6_node["id"], "data": data}
        if "parentId" in g6_node:
            node["parentId"] = g6_node["parentId"]
        style = g6_node.get("style")
        if style is not None and "x" in style and "y" in style:
            node["position"] = {"x": style["x"], "y": style["y"]}
        nodes.append(node)

    edges: list[ReactFlowEdge] = []
    for g6_edge in g6["edges"]:
        edge_data = g6_edge.get("data", {})
        edge: ReactFlowEdge = {
            "id": g6_edge["id"],
            "source": g6_edge["source"],
            "target": g6_edge["target"],
            "label": edge_data.get("label", ""),
        }
        if "order" in edge_data:
            edge["order"] = edge_data["order"]
        edges.append(edge)

    direction = "TB"
    if view.auto_layout is not None:
        direction = _RANK_DIRECTIONS.get(view.auto_layout.rank_direction, "TB")

    return {"nodes": nodes, "edges": edges, "rankDirection": direction}
