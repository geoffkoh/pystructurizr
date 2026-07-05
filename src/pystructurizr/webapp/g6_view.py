"""Translate a pystructurizr View into AntV G6 graph data."""

from __future__ import annotations

from typing import Any

from pystructurizr.models import (
    Location,
    Person,
    SoftwareSystem,
    View,
    ViewElement,
    ViewType,
    Workspace,
)


G6Node = dict[str, Any]
G6Edge = dict[str, Any]
G6Data = dict[str, list[Any]]


# Element-kind palette. Kept in Python so the JS bridge stays a thin shell
# and so tests can assert against it.
KIND_COLOURS: dict[str, str] = {
    "person": "#0d47a1",
    "person-external": "#546e7a",
    "system": "#1976d2",
    "system-external": "#90a4ae",
    "container": "#43a047",
    "component": "#fb8c00",
}


def _person_kind(p: Person) -> str:
    return "person-external" if p.location == Location.EXTERNAL else "person"


def _system_kind(s: SoftwareSystem) -> str:
    return "system-external" if s.location == Location.EXTERNAL else "system"


def _visible_ids(workspace: Workspace, view: View) -> set[str]:
    """Mirror MermaidGenerator._visible_ids so renderers stay in sync."""
    if view.include_all:
        ids: set[str] = set()
        ids.update(p.id for p in workspace.people)
        ids.update(s.id for s in workspace.software_systems)
        for s in workspace.software_systems:
            ids.update(c.id for c in s.containers)
            for c in s.containers:
                ids.update(comp.id for comp in c.components)
        return ids - set(view.excluded_ids)
    if view.included_ids:
        return set(view.included_ids) - set(view.excluded_ids)
    ids = set()
    if view.type == ViewType.SYSTEM_CONTEXT:
        ids.update(p.id for p in workspace.people)
        ids.update(s.id for s in workspace.software_systems)
    elif view.type == ViewType.CONTAINER:
        ids.update(p.id for p in workspace.people)
        ids.update(s.id for s in workspace.software_systems)
        for s in workspace.software_systems:
            if s.id == view.element_id:
                ids.update(c.id for c in s.containers)
    elif view.type == ViewType.COMPONENT:
        for s in workspace.software_systems:
            for c in s.containers:
                if c.id == view.element_id:
                    ids.update(comp.id for comp in c.components)
                else:
                    ids.add(c.id)
        ids.update(p.id for p in workspace.people)
    return ids


def _node(eid: str, label: str, kind: str, x: int | None = None, y: int | None = None) -> G6Node:
    """Build a G6 node descriptor.

    G6 v5 places nodes via ``style.x`` and ``style.y``. When positions
    are absent the layout engine (force-directed) will lay the node out
    on render.
    """
    node: G6Node = {
        "id": eid,
        "data": {"label": label, "kind": kind},
    }
    if x is not None and y is not None:
        node["style"] = {"x": x, "y": y}
    return node


def to_g6_data(workspace: Workspace, view: View) -> G6Data:
    """Return G6 graph data ``{nodes, edges}`` for the given view.

    Uses stored ViewElement positions when available so previously
    persisted layouts survive a re-render.
    """
    visible = _visible_ids(workspace, view)
    positions: dict[str, tuple[int, int]] = {
        ve.id: (ve.x, ve.y)
        for ve in view.element_views
        if ve.x is not None and ve.y is not None
    }

    def pos(eid: str) -> tuple[int | None, int | None]:
        xy = positions.get(eid)
        return xy if xy is not None else (None, None)

    nodes: list[G6Node] = []

    for p in workspace.people:
        if p.id in visible:
            x, y = pos(p.id)
            nodes.append(_node(p.id, p.name, _person_kind(p), x, y))

    for s in workspace.software_systems:
        if s.id in visible:
            x, y = pos(s.id)
            nodes.append(_node(s.id, s.name, _system_kind(s), x, y))
        for c in s.containers:
            if c.id in visible:
                x, y = pos(c.id)
                nodes.append(_node(c.id, c.name, "container", x, y))
            for comp in c.components:
                if comp.id in visible:
                    x, y = pos(comp.id)
                    nodes.append(_node(comp.id, comp.name, "component", x, y))

    edges: list[G6Edge] = []
    for rel in workspace.all_relationships_for(visible):
        edges.append({
            "id": rel.id or f"{rel.source_id}__{rel.destination_id}",
            "source": rel.source_id,
            "target": rel.destination_id,
            "data": {"label": rel.description},
        })

    return {"nodes": nodes, "edges": edges}


def apply_positions(view: View, positions: dict[str, tuple[int, int]]) -> None:
    """Update view.element_views with the given id → (x, y) positions.

    Adds a ViewElement for any id not already present. Existing entries
    are updated in place to preserve any other fields the user set.
    """
    existing = {ve.id: ve for ve in view.element_views}
    for eid, (x, y) in positions.items():
        ve = existing.get(eid)
        if ve is None:
            view.element_views.append(ViewElement(id=eid, x=x, y=y))
        else:
            ve.x = x
            ve.y = y
