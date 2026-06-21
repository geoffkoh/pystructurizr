"""Translate a pystructurizr View into Cytoscape.js elements."""

from __future__ import annotations

from typing import Any

from pystructurizr.models import (
    Component,
    Container,
    Location,
    Person,
    SoftwareSystem,
    View,
    ViewType,
    Workspace,
)


CytoscapeElement = dict[str, Any]


def _person_kind(p: Person) -> str:
    return "person-external" if p.location == Location.EXTERNAL else "person"


def _system_kind(s: SoftwareSystem) -> str:
    return "system-external" if s.location == Location.EXTERNAL else "system"


def _visible_ids(workspace: Workspace, view: View) -> set[str]:
    """Mirror MermaidGenerator._visible_ids so the two canvases stay in sync."""
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


def _node(eid: str, label: str, kind: str, x: int | None = None, y: int | None = None) -> CytoscapeElement:
    data: CytoscapeElement = {"data": {"id": eid, "label": label, "kind": kind}}
    if x is not None and y is not None:
        data["position"] = {"x": x, "y": y}
    return data


def to_cytoscape_elements(workspace: Workspace, view: View) -> list[CytoscapeElement]:
    """Return a Cytoscape elements list (nodes + edges) for the given view."""
    visible = _visible_ids(workspace, view)
    nodes: list[CytoscapeElement] = []

    for p in workspace.people:
        if p.id in visible:
            nodes.append(_node(p.id, p.name, _person_kind(p)))

    for s in workspace.software_systems:
        if s.id in visible:
            nodes.append(_node(s.id, s.name, _system_kind(s)))
        for c in s.containers:
            if c.id in visible:
                nodes.append(_node(c.id, c.name, "container"))
            for comp in c.components:
                if comp.id in visible:
                    nodes.append(_node(comp.id, comp.name, "component"))

    edges: list[CytoscapeElement] = []
    for rel in workspace.all_relationships_for(visible):
        edges.append({
            "data": {
                "id": rel.id or f"{rel.source_id}__{rel.destination_id}",
                "source": rel.source_id,
                "target": rel.destination_id,
                "label": rel.description,
            }
        })

    return nodes + edges


# Cytoscape stylesheet expressed as plain dicts — serialized to JS as-is.
DEFAULT_STYLESHEET: list[CytoscapeElement] = [
    {
        "selector": "node",
        "style": {
            "label": "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "font-size": "11px",
            "color": "#fff",
            "background-color": "#1976d2",
            "shape": "round-rectangle",
            "width": "140px",
            "height": "70px",
            "border-width": 1,
            "border-color": "#0d47a1",
        },
    },
    {"selector": "node[kind = 'person']", "style": {"background-color": "#0d47a1", "shape": "round-rectangle"}},
    {"selector": "node[kind = 'person-external']", "style": {"background-color": "#546e7a"}},
    {"selector": "node[kind = 'system']", "style": {"background-color": "#1976d2"}},
    {"selector": "node[kind = 'system-external']", "style": {"background-color": "#90a4ae"}},
    {"selector": "node[kind = 'container']", "style": {"background-color": "#43a047"}},
    {"selector": "node[kind = 'component']", "style": {"background-color": "#fb8c00"}},
    {
        "selector": "edge",
        "style": {
            "label": "data(label)",
            "font-size": "10px",
            "color": "#555",
            "text-background-color": "#fff",
            "text-background-opacity": 0.85,
            "text-background-padding": "2px",
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "#90a4ae",
            "target-arrow-color": "#90a4ae",
            "width": 1.5,
        },
    },
]
