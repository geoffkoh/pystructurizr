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
    DeploymentNode,
    Location,
    Person,
    Relationship,
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
    "infrastructure": "#607d8b",
    "container-instance": "#43a047",
    "system-instance": "#1976d2",
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

    if view.type == ViewType.SYSTEM_LANDSCAPE:
        return set(people) | set(systems)

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


# Implicit Structurizr tag per node kind, used for tag-based style matching.
_IMPLICIT_TAGS: dict[str, str] = {
    "person": "Person",
    "person-external": "Person",
    "system": "Software System",
    "system-external": "Software System",
    "container": "Container",
    "component": "Component",
    "infrastructure": "Infrastructure Node",
    "container-instance": "Container Instance",
    "system-instance": "Software System Instance",
}


def _apply_styles(workspace: Workspace, nodes: list[G6Node]) -> None:
    """Overlay tag-based element styles onto node data, in place.

    Mirrors Structurizr style resolution: every element implicitly carries
    the ``Element`` tag plus a tag for its kind, then its own tags; element
    style rules are applied in declaration order, later matches overriding
    earlier ones. Applied properties land in node data as ``background``,
    ``textColor`` and ``shape``.
    """
    styles = workspace.views.configuration.styles.element_styles
    if not styles:
        return
    for node in nodes:
        data = node["data"]
        implicit = _IMPLICIT_TAGS.get(data.get("kind", ""))
        if implicit is None:
            continue
        tags = {"Element", implicit, *data.get("tags", [])}
        for style in styles:
            if style.tag not in tags:
                continue
            if style.background:
                data["background"] = style.background
            if style.color:
                data["textColor"] = style.color
            if style.shape is not None:
                data["shape"] = style.shape.value


def _deployment_data(workspace: Workspace, view: View) -> G6Data:
    """Build graph data for a deployment view.

    Deployment nodes render as (arbitrarily) nested boundary group nodes;
    infrastructure nodes and container/system instances are their leaves.
    Branches containing no instance relevant to the view's scope/environment
    are pruned. Edges come from relationships declared directly between
    deployment elements plus relationships derived from the model: when two
    deployed elements' underlying model elements are related, their
    instances are too.
    """
    env = view.environment
    scope = view.element_id
    parents = _parent_ids(workspace)
    systems = {s.id: s for s in workspace.software_systems}
    container_system: dict[str, SoftwareSystem] = {}
    containers: dict[str, Container] = {}
    for s in workspace.software_systems:
        for c in s.containers:
            containers[c.id] = c
            container_system[c.id] = s

    def relevant_container(inst_container_id: str) -> bool:
        if not scope:
            return True
        s = container_system.get(inst_container_id)
        return s is not None and s.id == scope

    def relevant_system(system_id: str) -> bool:
        return not scope or system_id == scope

    def subtree_relevant(dn: DeploymentNode) -> bool:
        if any(relevant_container(i.container_id) for i in dn.container_instances):
            return True
        if any(
            relevant_system(i.software_system_id) for i in dn.software_system_instances
        ):
            return True
        return any(subtree_relevant(child) for child in dn.children)

    nodes: list[G6Node] = []
    instance_refs: dict[str, str] = {}  # leaf id -> underlying model element id
    leaf_ids: set[str] = set()

    def leaf(
        eid: str,
        label: str,
        kind: str,
        technology: str,
        description: str,
        tags: list[str],
        parent_id: str,
    ) -> None:
        nodes.append(
            {
                "id": eid,
                "parentId": parent_id,
                "data": {
                    "label": label,
                    "kind": kind,
                    "technology": technology,
                    "description": description,
                    "tags": tags,
                },
            }
        )
        leaf_ids.add(eid)

    def emit(dn: DeploymentNode, parent_id: str | None) -> None:
        if env and dn.environment and dn.environment != env:
            return
        if not subtree_relevant(dn):
            return
        boundary: G6Node = {
            "id": dn.id,
            "data": {
                "label": dn.name,
                "kind": "boundary",
                "technology": dn.technology,
                "description": dn.description,
                "tags": list(dn.tags),
                "boundaryLabel": "Deployment Node",
            },
        }
        if parent_id is not None:
            boundary["parentId"] = parent_id
        nodes.append(boundary)
        for infra in dn.infrastructure_nodes:
            leaf(
                infra.id,
                infra.name,
                "infrastructure",
                infra.technology,
                infra.description,
                list(infra.tags),
                dn.id,
            )
        for ssi in dn.software_system_instances:
            if relevant_system(ssi.software_system_id):
                s = systems.get(ssi.software_system_id)
                leaf(
                    ssi.id,
                    s.name if s else ssi.software_system_id,
                    "system-instance",
                    "",
                    s.description if s else "",
                    list(ssi.tags) + (list(s.tags) if s else []),
                    dn.id,
                )
                instance_refs[ssi.id] = ssi.software_system_id
        for ci in dn.container_instances:
            if relevant_container(ci.container_id):
                c = containers.get(ci.container_id)
                leaf(
                    ci.id,
                    c.name if c else ci.container_id,
                    "container-instance",
                    c.technology if c else "",
                    c.description if c else "",
                    list(ci.tags) + (list(c.tags) if c else []),
                    dn.id,
                )
                instance_refs[ci.id] = ci.container_id
        for child in dn.children:
            emit(child, dn.id)

    for dn in workspace.deployment_nodes:
        emit(dn, None)

    # Invert instance refs for deriving instance-level edges from the model.
    ref_instances: dict[str, list[str]] = {}
    for inst_id, ref_id in instance_refs.items():
        ref_instances.setdefault(ref_id, []).append(inst_id)
    ref_ids = set(ref_instances)

    edges: list[G6Edge] = []
    seen: set[tuple[str, str]] = set()

    def add_edge(src: str, dst: str, rel: Relationship) -> None:
        if src == dst or (src, dst) in seen:
            return
        seen.add((src, dst))
        edges.append(
            {
                "id": f"{src}__{dst}__{len(edges)}",
                "source": src,
                "target": dst,
                "data": {"label": rel.description, "technology": rel.technology},
            }
        )

    for rel in workspace.relationships:
        # Relationships declared directly between deployment elements.
        if rel.source_id in leaf_ids and rel.destination_id in leaf_ids:
            add_edge(rel.source_id, rel.destination_id, rel)
            continue
        # Model relationships replicated onto every pair of instances.
        src_ref = _lift(rel.source_id, ref_ids, parents)
        dst_ref = _lift(rel.destination_id, ref_ids, parents)
        if src_ref is None or dst_ref is None or src_ref == dst_ref:
            continue
        for src_inst in ref_instances[src_ref]:
            for dst_inst in ref_instances[dst_ref]:
                add_edge(src_inst, dst_inst, rel)

    _apply_styles(workspace, nodes)
    return {"nodes": nodes, "edges": edges}


def to_g6_data(
    workspace: Workspace, view: View, expand: set[str] | None = None
) -> G6Data:
    """Return graph data ``{nodes, edges}`` for the given view.

    Boundary group nodes always precede their children in the node list so
    the frontend can render parents behind children. Stored ViewElement
    positions are applied when available so previously persisted layouts
    survive a re-render.

    Args:
        workspace: The workspace to render from.
        view: The view to render.
        expand: For container views, ids of containers to expand in place —
            each becomes a nested boundary containing its components.
    """
    if view.type == ViewType.DEPLOYMENT:
        return _deployment_data(workspace, view)

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

    # In container views, requested containers with components expand into
    # nested boundaries holding their components.
    expanded: set[str] = set()
    if expand and view.type == ViewType.CONTAINER:
        all_containers = {
            c.id: c for s in workspace.software_systems for c in s.containers
        }
        expanded = {
            cid for cid in expand if cid in visible and all_containers[cid].components
        }
        visible -= expanded
        for cid in expanded:
            visible.update(comp.id for comp in all_containers[cid].components)

    nodes: list[G6Node] = []

    # Landscape views group internal elements inside the enterprise
    # boundary when one is defined.
    enterprise_id: str | None = None
    if view.type == ViewType.SYSTEM_LANDSCAPE and workspace.enterprise is not None:
        enterprise_id = "__enterprise__"
        nodes.append(
            {
                "id": enterprise_id,
                "data": {
                    "label": workspace.enterprise.name,
                    "kind": "boundary",
                    "technology": "",
                    "description": "",
                    "tags": [],
                    "boundaryLabel": "Enterprise",
                },
            }
        )

    boundary_id: str | None = None
    scope = _boundary_scope(workspace, view)
    if scope is not None:
        boundary_id, boundary_element = scope
        # The scoped element is the boundary, never a leaf peer.
        visible.discard(boundary_id)
        x, y = pos(boundary_id)
        boundary_node = _node(boundary_id, boundary_element, "boundary", x, y)
        boundary_node["data"]["boundaryLabel"] = (
            "Container" if view.type == ViewType.COMPONENT else "Software System"
        )
        nodes.append(boundary_node)

    def child_of(eid: str) -> str | None:
        parent = parents.get(eid)
        if parent == boundary_id:
            return boundary_id
        if parent in expanded:
            return parent
        return None

    def enterprise_parent(kind: str) -> str | None:
        if enterprise_id is not None and not kind.endswith("-external"):
            return enterprise_id
        return None

    for p in workspace.people:
        if p.id in visible:
            x, y = pos(p.id)
            kind = _person_kind(p)
            nodes.append(_node(p.id, p, kind, x, y, enterprise_parent(kind)))

    for s in workspace.software_systems:
        if s.id in visible:
            x, y = pos(s.id)
            kind = _system_kind(s)
            nodes.append(_node(s.id, s, kind, x, y, enterprise_parent(kind)))
        for c in s.containers:
            if c.id in expanded:
                x, y = pos(c.id)
                group = _node(c.id, c, "boundary", x, y, child_of(c.id))
                group["data"]["boundaryLabel"] = "Container"
                group["data"]["expanded"] = True
                nodes.append(group)
            elif c.id in visible:
                x, y = pos(c.id)
                node = _node(c.id, c, "container", x, y, child_of(c.id))
                if view.type == ViewType.CONTAINER and c.components:
                    node["data"]["expandable"] = True
                nodes.append(node)
            for comp in c.components:
                if comp.id in visible:
                    x, y = pos(comp.id)
                    nodes.append(
                        _node(comp.id, comp, "component", x, y, child_of(comp.id))
                    )

    _apply_styles(workspace, nodes)
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
