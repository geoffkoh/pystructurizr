"""
Structurizr JSON parser.

Reads the JSON export format produced by the Structurizr tooling and converts
it into the pystructurizr model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pystructurizr.models import (
    Component,
    Container,
    Person,
    Relationship,
    SoftwareSystem,
    View,
    ViewType,
    Workspace,
)


def _tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _parse_person(data: dict[str, Any]) -> Person:
    return Person(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        tags=_tags(data.get("tags")),
        external="External" in _tags(data.get("tags")),
    )


def _parse_component(data: dict[str, Any]) -> Component:
    return Component(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        technology=data.get("technology", ""),
        tags=_tags(data.get("tags")),
    )


def _parse_container(data: dict[str, Any]) -> Container:
    components = [_parse_component(c) for c in data.get("components", [])]
    return Container(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        technology=data.get("technology", ""),
        components=components,
        tags=_tags(data.get("tags")),
    )


def _parse_software_system(data: dict[str, Any]) -> SoftwareSystem:
    containers = [_parse_container(c) for c in data.get("containers", [])]
    return SoftwareSystem(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        containers=containers,
        tags=_tags(data.get("tags")),
        external="External" in _tags(data.get("tags")),
    )


def _parse_relationship(data: dict[str, Any]) -> Relationship:
    return Relationship(
        source_id=data["sourceId"],
        destination_id=data["destinationId"],
        description=data.get("description", ""),
        technology=data.get("technology", ""),
        tags=_tags(data.get("tags")),
    )


def _parse_view(data: dict[str, Any], view_type: ViewType) -> View:
    included_ids = [e["id"] for e in data.get("elements", [])]
    include_all = "*" in data.get("includes", [])
    return View(
        type=view_type,
        key=data.get("key", ""),
        element_id=data.get("softwareSystemId", data.get("containerId", "")),
        title=data.get("title", ""),
        description=data.get("description", ""),
        include_all=include_all or bool(included_ids),
        included_ids=included_ids,
        auto_layout="automaticLayout" in data,
    )


def parse_json(source: str) -> Workspace:
    """Parse a Structurizr JSON string and return a Workspace."""
    data = json.loads(source)
    return _parse_json_dict(data)


def parse_json_file(path: str | Path) -> Workspace:
    """Read a .json file and parse it."""
    return parse_json(Path(path).read_text(encoding="utf-8"))


def _parse_json_dict(data: dict[str, Any]) -> Workspace:
    ws_data = data.get("workspace", data)
    model = ws_data.get("model", {})
    views_data = ws_data.get("views", {})

    people = [_parse_person(p) for p in model.get("people", [])]
    software_systems = [_parse_software_system(s) for s in model.get("softwareSystems", [])]

    # collect all relationships (may live on individual elements too)
    relationships: list[Relationship] = []
    for r in model.get("relationships", []):
        relationships.append(_parse_relationship(r))
    for person in model.get("people", []):
        for r in person.get("relationships", []):
            r["sourceId"] = person["id"]
            relationships.append(_parse_relationship(r))
    for system in model.get("softwareSystems", []):
        for r in system.get("relationships", []):
            r["sourceId"] = system["id"]
            relationships.append(_parse_relationship(r))
        for container in system.get("containers", []):
            for r in container.get("relationships", []):
                r["sourceId"] = container["id"]
                relationships.append(_parse_relationship(r))
            for component in container.get("components", []):
                for r in component.get("relationships", []):
                    r["sourceId"] = component["id"]
                    relationships.append(_parse_relationship(r))

    views: list[View] = []
    for v in views_data.get("systemContextViews", []):
        views.append(_parse_view(v, ViewType.SYSTEM_CONTEXT))
    for v in views_data.get("containerViews", []):
        views.append(_parse_view(v, ViewType.CONTAINER))
    for v in views_data.get("componentViews", []):
        views.append(_parse_view(v, ViewType.COMPONENT))
    for v in views_data.get("dynamicViews", []):
        views.append(_parse_view(v, ViewType.DYNAMIC))
    for v in views_data.get("deploymentViews", []):
        views.append(_parse_view(v, ViewType.DEPLOYMENT))

    return Workspace(
        name=ws_data.get("name", ""),
        description=ws_data.get("description", ""),
        people=people,
        software_systems=software_systems,
        relationships=relationships,
        views=views,
    )
