"""Translate a pystructurizr View into graph data for the web frontend.

Visibility follows Structurizr view semantics: each view type exposes only
the elements at its abstraction level (a system context view never shows
containers), scoped to the view's subject element. Relationships whose
endpoints are not directly visible are "lifted" to their nearest visible
ancestor so, for example, a ``person -> container`` relationship still
produces a ``person -> system`` edge on a context diagram.

For container and component views the scoped element is emitted as a
``boundary`` group node and its direct children carry a ``parentId`` so the
frontend can nest them inside the boundary, matching C4 rendering
conventions.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pystructurizr.models import (
    Component,
    Container,
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

_Element = Person | SoftwareSystem | Container | Component


# Element-kind palette. Kept in Python so the JS bridge stays a thin shell
# and so tests can assert against it.
KIND_COLOURS: dict[str, str] = {
    "person": "#0d47a1",
    "person-external": "#546e7a",
    "system": "#1976d2",
    "system-external": "#90a4ae",
    "container": "#43a047",
    "component": "#fb8c00",
    "boundary": "#90a4ae",
}


def _is_external(location: Location, tags: list[str]) -> bool:
    """Whether an element is external, via location or an "external" tag.

    Structurizr models commonly mark externals with a tag such as
    ``External System`` rather than the ``location`` property, so both are
    honoured.
    """
    if location == Location.EXTERNAL:
        return True
    return any("external" in tag.lower() for tag in tags)


def _person_kind(p: Person) -> str:
    return "person-external" if _is_external(p.location, p.tags) else "person"


def _system_kind(s: SoftwareSystem) -> str:
    return "system-external" if _is_external(s.location, s.tags) else "system"


def _parent_ids(workspace: Workspace) -> dict[str, str]:
    """Map each container/component id to its parent element's id."""
    parents: dict[str, str] = {}
    for s in workspace.software_systems:
        for c in s.containers:
            parents[c.id] = s.id
            for comp in c.components:
                parents[comp.id] = c.id
    return parents


def _ancestry(eid: str, parents: dict[str, str]) -> list[str]:
    """Return ``eid`` followed by its ancestors, innermost first."""
    chain = [eid]
    while chain[-1] in parents:
        chain.append(parents[chain[-1]])
    return chain


def _lift_to(eid: str, allowed: set[str], parents: dict[str, str]) -> str | None:
    """Return the most specific ancestor of ``eid`` present in ``allowed``."""
    for ancestor in _ancestry(eid, parents):
        if ancestor in allowed:
            return ancestor
    return None


def _related_peers(
    workspace: Workspace,
    scope_id: str,
    allowed: Iterable[str],
    parents: dict[str, str],
    include_scope_level: bool,
) -> set[str]:
    """Return peers outside the scope that relate to elements inside it.

    For each relationship crossing the scope boundary, the outside endpoint
    is lifted to the most specific allowed element and only that element is
    added — so a relationship declared against a container surfaces that
    container, not additionally its parent system (which would float
    unconnected once edges attach to the container).

    Args:
        workspace: The workspace being rendered.
        scope_id: The view's subject element.
        allowed: Ids of elements permitted to appear as peers in this view.
        parents: Child-to-parent id mapping.
        include_scope_level: Whether relationships declared against the
            scope element itself (rather than a descendant) count. True for
            context views, where the scope is itself a node; False where
            the scope renders as a boundary and such edges cannot attach.
    """
    allowed_set = set(allowed)
    peers: set[str] = set()
    for rel in workspace.relationships:
        endpoints = (
            (rel.source_id, rel.destination_id),
            (rel.destination_id, rel.source_id),
        )
        for inner, outer in endpoints:
            if scope_id not in _ancestry(inner, parents):
                continue
            if not include_scope_level and inner == scope_id:
                continue
            if scope_id in _ancestry(outer, parents):
                continue
            lifted = _lift_to(outer, allowed_set, parents)
            if lifted is not None:
                peers.add(lifted)
    return peers


def _default_ids(workspace: Workspace, view: View, parents: dict[str, str]) -> set[str]:
    """Return the default visible ids for a view (``include *`` semantics).

    Each view type exposes only the elements at its abstraction level; when
    the view has a scope element, peers are those with a relationship into
    the scope, surfaced at the level the relationship was declared.
    """
    scope = view.element_id
    people = [p.id for p in workspace.people]
    systems = [s.id for s in workspace.software_systems]

    if view.type == ViewType.SYSTEM_CONTEXT:
        allowed = people + [sid for sid in systems if sid != scope]
        if not scope:
            return set(allowed)
        ids = _related_peers(
            workspace, scope, allowed, parents, include_scope_level=True
        )
        ids.add(scope)
        return ids

    if view.type == ViewType.CONTAINER:
        ids = set()
        for s in workspace.software_systems:
            if s.id == scope:
                ids.update(c.id for c in s.containers)
        allowed = people + [sid for sid in systems if sid != scope]
        if scope:
            ids |= _related_peers(
                workspace, scope, allowed, parents, include_scope_level=False
            )
        else:
            ids.update(allowed)
        return ids

    if view.type == ViewType.COMPONENT:
        ids = set()
        parent_system_id = parents.get(scope, "")
        allowed = list(people)
        for s in workspace.software_systems:
            if s.id != parent_system_id:
                allowed.append(s.id)
            for c in s.containers:
                if c.id == scope:
                    ids.update(comp.id for comp in c.components)
                else:
                    allowed.append(c.id)
        if scope:
            ids |= _related_peers(
                workspace, scope, allowed, parents, include_scope_level=False
            )
        else:
            ids.update(allowed)
        return ids

    return set()


def _visible_ids(workspace: Workspace, view: View) -> set[str]:
    """Return the ids of elements visible in ``view``.

    Explicitly included ids are honoured as-is; otherwise the view falls back
    to its type-scoped defaults (which is also what ``include *`` means).
    Exclusions always apply last.
    """
    parents = _parent_ids(workspace)
    if view.included_ids:
        visible = set(view.included_ids)
    else:
        visible = _default_ids(workspace, view, parents)
    return visible - set(view.excluded_ids)


def _lift(eid: str, visible: set[str], parents: dict[str, str]) -> str | None:
    """Return the nearest visible ancestor of ``eid`` (or ``eid`` itself)."""
    for ancestor in _ancestry(eid, parents):
        if ancestor in visible:
            return ancestor
    return None


def _node(
    eid: str,
    element: _Element,
    kind: str,
    x: int | None = None,
    y: int | None = None,
    parent_id: str | None = None,
) -> G6Node:
    """Build a graph node descriptor.

    Positions are stored under ``style.x``/``style.y``; when absent the
    frontend layout engine places the node. ``parentId`` marks the node as a
    child of a boundary group node.
    """
    node: G6Node = {
        "id": eid,
        "data": {
            "label": element.name,
            "kind": kind,
            "technology": getattr(element, "technology", ""),
            "description": element.description,
            "tags": list(element.tags),
        },
    }
    if parent_id is not None:
        node["parentId"] = parent_id
    if x is not None and y is not None:
        node["style"] = {"x": x, "y": y}
    return node


def _boundary_scope(
    workspace: Workspace, view: View
) -> tuple[str, SoftwareSystem | Container] | None:
    """Return the (id, element) rendered as this view's boundary, if any."""
    if view.type == ViewType.CONTAINER:
        for s in workspace.software_systems:
            if s.id == view.element_id:
                return s.id, s
    elif view.type == ViewType.COMPONENT:
        for s in workspace.software_systems:
            for c in s.containers:
                if c.id == view.element_id:
                    return c.id, c
    return None


def _edges(
    workspace: Workspace, visible: set[str], parents: dict[str, str]
) -> list[G6Edge]:
    """Build edges between visible nodes, lifting endpoints to ancestors.

    Lifted duplicates collapse into a single implied edge per (source,
    target) pair; distinct direct relationships between the same pair are
    kept (e.g. separate "Reads" and "Writes" relationships).
    """
    edges: list[G6Edge] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_direct: set[tuple[str, str, str]] = set()
    for rel in workspace.relationships:
        src = _lift(rel.source_id, visible, parents)
        dst = _lift(rel.destination_id, visible, parents)
        if src is None or dst is None or src == dst:
            continue
        lifted = src != rel.source_id or dst != rel.destination_id
        if lifted:
            if (src, dst) in seen_pairs:
                continue
        else:
            key = (src, dst, rel.description)
            if key in seen_direct:
                continue
            seen_direct.add(key)
        seen_pairs.add((src, dst))
        edges.append(
            {
                "id": rel.id or f"{src}__{dst}__{len(edges)}",
                "source": src,
                "target": dst,
                "data": {"label": rel.description, "technology": rel.technology},
            }
        )
    return edges


def to_g6_data(workspace: Workspace, view: View) -> G6Data:
    """Return graph data ``{nodes, edges}`` for the given view.

    The boundary group node (when the view has one) is always first in the
    node list so the frontend can render it behind its children. Stored
    ViewElement positions are applied when available so previously persisted
    layouts survive a re-render.
    """
    parents = _parent_ids(workspace)
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

    boundary_id: str | None = None
    scope = _boundary_scope(workspace, view)
    if scope is not None:
        boundary_id, boundary_element = scope
        # The scoped element is the boundary, never a leaf peer.
        visible.discard(boundary_id)
        x, y = pos(boundary_id)
        nodes.append(_node(boundary_id, boundary_element, "boundary", x, y))

    def child_of(eid: str) -> str | None:
        return boundary_id if parents.get(eid) == boundary_id else None

    for p in workspace.people:
        if p.id in visible:
            x, y = pos(p.id)
            nodes.append(_node(p.id, p, _person_kind(p), x, y))

    for s in workspace.software_systems:
        if s.id in visible:
            x, y = pos(s.id)
            nodes.append(_node(s.id, s, _system_kind(s), x, y))
        for c in s.containers:
            if c.id in visible:
                x, y = pos(c.id)
                nodes.append(_node(c.id, c, "container", x, y, child_of(c.id)))
            for comp in c.components:
                if comp.id in visible:
                    x, y = pos(comp.id)
                    nodes.append(
                        _node(comp.id, comp, "component", x, y, child_of(comp.id))
                    )

    return {"nodes": nodes, "edges": _edges(workspace, visible, parents)}


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
