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
    Animation,
    AutomaticLayout,
    Component,
    Configuration,
    Container,
    ContainerInstance,
    DeploymentNode,
    ElementStyle,
    HttpHealthCheck,
    InfrastructureNode,
    Location,
    Person,
    Perspective,
    RankDirection,
    Relationship,
    RelationshipStyle,
    RelationshipView,
    SoftwareSystem,
    SoftwareSystemInstance,
    Styles,
    Terminology,
    View,
    ViewType,
    Workspace,
)


def _tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]


def _properties(raw: dict[str, Any] | None) -> dict[str, str]:
    if not raw:
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _perspectives(raw: list[dict[str, Any]] | None) -> list[Perspective]:
    if not raw:
        return []
    return [
        Perspective(
            name=p.get("name", ""),
            description=p.get("description", ""),
            value=p.get("value", ""),
            url=p.get("url", ""),
        )
        for p in raw
    ]


def _location(tag_list: list[str]) -> Location:
    if "External" in tag_list:
        return Location.EXTERNAL
    if "Internal" in tag_list:
        return Location.INTERNAL
    return Location.UNSPECIFIED


def _parse_person(data: dict[str, Any]) -> Person:
    tag_list = _tags(data.get("tags"))
    return Person(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        tags=tag_list,
        location=_location(tag_list),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
        group=data.get("group", ""),
    )


def _parse_component(data: dict[str, Any]) -> Component:
    return Component(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        technology=data.get("technology", ""),
        tags=_tags(data.get("tags")),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
        group=data.get("group", ""),
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
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
        group=data.get("group", ""),
    )


def _parse_software_system(data: dict[str, Any]) -> SoftwareSystem:
    tag_list = _tags(data.get("tags"))
    containers = [_parse_container(c) for c in data.get("containers", [])]
    return SoftwareSystem(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        containers=containers,
        tags=tag_list,
        location=_location(tag_list),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
        group=data.get("group", ""),
    )


def _parse_relationship(data: dict[str, Any]) -> Relationship:
    return Relationship(
        id=data.get("id", ""),
        source_id=data["sourceId"],
        destination_id=data["destinationId"],
        description=data.get("description", ""),
        technology=data.get("technology", ""),
        tags=_tags(data.get("tags")),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
    )


def _parse_health_checks(raw: list[dict[str, Any]] | None) -> list[HttpHealthCheck]:
    if not raw:
        return []
    return [
        HttpHealthCheck(
            name=h.get("name", ""),
            url=h.get("url", ""),
            interval=int(h.get("interval", 60)),
            timeout=int(h.get("timeout", 0)),
            headers=_properties(h.get("headers")),
        )
        for h in raw
    ]


def _parse_software_system_instance(data: dict[str, Any]) -> SoftwareSystemInstance:
    return SoftwareSystemInstance(
        id=data["id"],
        software_system_id=data.get("softwareSystemId", ""),
        instance_id=int(data.get("instanceId", 1)),
        environment=data.get("environment", ""),
        deployment_groups=data.get("deploymentGroups", []),
        health_checks=_parse_health_checks(data.get("healthChecks")),
        tags=_tags(data.get("tags")),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
    )


def _parse_container_instance(data: dict[str, Any]) -> ContainerInstance:
    return ContainerInstance(
        id=data["id"],
        container_id=data.get("containerId", ""),
        instance_id=int(data.get("instanceId", 1)),
        environment=data.get("environment", ""),
        deployment_groups=data.get("deploymentGroups", []),
        health_checks=_parse_health_checks(data.get("healthChecks")),
        tags=_tags(data.get("tags")),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
    )


def _parse_infrastructure_node(data: dict[str, Any]) -> InfrastructureNode:
    return InfrastructureNode(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        technology=data.get("technology", ""),
        tags=_tags(data.get("tags")),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
        group=data.get("group", ""),
        icon=data.get("icon", ""),
    )


def _parse_deployment_node(data: dict[str, Any]) -> DeploymentNode:
    children = [_parse_deployment_node(c) for c in data.get("children", [])]
    infrastructure_nodes = [_parse_infrastructure_node(n) for n in data.get("infrastructureNodes", [])]
    software_system_instances = [
        _parse_software_system_instance(i) for i in data.get("softwareSystemInstances", [])
    ]
    container_instances = [
        _parse_container_instance(i) for i in data.get("containerInstances", [])
    ]
    return DeploymentNode(
        id=data["id"],
        name=data.get("name", ""),
        description=data.get("description", ""),
        technology=data.get("technology", ""),
        instances=str(data.get("instances", "1")),
        environment=data.get("environment", ""),
        tags=_tags(data.get("tags")),
        url=data.get("url", ""),
        properties=_properties(data.get("properties")),
        perspectives=_perspectives(data.get("perspectives")),
        group=data.get("group", ""),
        icon=data.get("icon", ""),
        children=children,
        infrastructure_nodes=infrastructure_nodes,
        software_system_instances=software_system_instances,
        container_instances=container_instances,
        deployment_groups=data.get("deploymentGroups", []),
    )


def _parse_auto_layout(data: dict[str, Any] | None) -> AutomaticLayout | None:
    if data is None:
        return None
    _RANK_MAP: dict[str, RankDirection] = {
        "TopBottom": RankDirection.TOP_BOTTOM,
        "BottomTop": RankDirection.BOTTOM_TOP,
        "LeftRight": RankDirection.LEFT_RIGHT,
        "RightLeft": RankDirection.RIGHT_LEFT,
    }
    rank_dir = _RANK_MAP.get(data.get("rankDirection", ""), RankDirection.TOP_BOTTOM)
    return AutomaticLayout(
        rank_direction=rank_dir,
        rank_separation=int(data.get("rankSeparation", 300)),
        node_separation=int(data.get("nodeSeparation", 300)),
        edge_separation=int(data.get("edgeSeparation", 0)),
        vertices=bool(data.get("vertices", False)),
    )


def _parse_relationship_view(data: dict[str, Any]) -> RelationshipView:
    return RelationshipView(
        id=data.get("id", ""),
        description=data.get("description", ""),
        url=data.get("url", ""),
        order=str(data.get("order", "")),
        response=data.get("response"),
        properties=_properties(data.get("properties")),
        title=data.get("title", ""),
        link=data.get("link"),
        link_element=data.get("linkElement"),
    )


def _parse_animation(data: dict[str, Any], order: int) -> Animation:
    return Animation(
        order=order,
        element_ids=data.get("elements", []),
        relationship_ids=data.get("relationships", []),
    )


def _parse_view(data: dict[str, Any], view_type: ViewType) -> View:
    included_ids = [e["id"] for e in data.get("elements", [])]
    include_all = "*" in data.get("includes", [])
    relationship_views = [_parse_relationship_view(r) for r in data.get("relationships", [])]
    animations = [
        _parse_animation(a, i + 1) for i, a in enumerate(data.get("animations", []))
    ]
    return View(
        type=view_type,
        key=data.get("key", ""),
        element_id=data.get("softwareSystemId", data.get("containerId", data.get("elementId", ""))),
        title=data.get("title", ""),
        description=data.get("description", ""),
        include_all=include_all or bool(included_ids),
        included_ids=included_ids,
        auto_layout=_parse_auto_layout(data.get("automaticLayout")),
        order=int(data.get("order", 0)),
        properties=_properties(data.get("properties")),
        relationship_views=relationship_views,
        animations=animations,
        owner=data.get("owner", ""),
        disable_automatic_layout=bool(data.get("disableAutomaticLayout", False)),
        hide_element_metadata=bool(data.get("hideElementMetadata", False)),
        hide_relationship_metadata=bool(data.get("hideRelationshipMetadata", False)),
    )


def _parse_element_style(data: dict[str, Any]) -> ElementStyle:
    return ElementStyle(
        tag=data.get("tag", ""),
        background=data.get("background", ""),
        stroke=data.get("stroke", ""),
        color=data.get("color", ""),
        icon=data.get("icon", ""),
        width=data.get("width"),
        height=data.get("height"),
        stroke_width=data.get("strokeWidth"),
        font_size=data.get("fontSize"),
        opacity=data.get("opacity"),
        metadata=data.get("metadata"),
        description=data.get("description"),
    )


def _parse_relationship_style(data: dict[str, Any]) -> RelationshipStyle:
    return RelationshipStyle(
        tag=data.get("tag", ""),
        color=data.get("color", ""),
        thickness=data.get("thickness"),
        font_size=data.get("fontSize"),
        width=data.get("width"),
        dashed=data.get("dashed"),
        position=data.get("position"),
        opacity=data.get("opacity"),
        metadata=data.get("metadata"),
        description=data.get("description"),
    )


def _parse_configuration(data: dict[str, Any] | None) -> Configuration:
    if not data:
        return Configuration()
    styles_data = data.get("styles", {})
    element_styles = [_parse_element_style(s) for s in styles_data.get("elements", [])]
    relationship_styles = [_parse_relationship_style(s) for s in styles_data.get("relationships", [])]
    terminology_data = data.get("terminology", {})
    terminology = Terminology(
        enterprise=terminology_data.get("enterprise", ""),
        person=terminology_data.get("person", ""),
        software_system=terminology_data.get("softwareSystem", ""),
        container=terminology_data.get("container", ""),
        component=terminology_data.get("component", ""),
        code=terminology_data.get("code", ""),
        deployment_node=terminology_data.get("deploymentNode", ""),
        infrastructure_node=terminology_data.get("infrastructureNode", ""),
        relationship=terminology_data.get("relationship", ""),
    )
    return Configuration(
        styles=Styles(element_styles=element_styles, relationship_styles=relationship_styles),
        themes=data.get("themes", []),
        terminology=terminology,
        default_view=data.get("defaultView", ""),
        properties=_properties(data.get("properties")),
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
    deployment_nodes = [_parse_deployment_node(n) for n in model.get("deploymentNodes", [])]
    deployment_environments = list(model.get("deploymentEnvironments", []))

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
    for v in views_data.get("systemLandscapeViews", []):
        views.append(_parse_view(v, ViewType.SYSTEM_LANDSCAPE))
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
        deployment_nodes=deployment_nodes,
        deployment_environments=deployment_environments,
        configuration=_parse_configuration(ws_data.get("views", {}).get("configuration")),
        id=str(ws_data.get("id", "")),
        version=int(ws_data.get("version", 1)),
        revision=int(ws_data.get("revision", 1)),
        last_modified_date=ws_data.get("lastModifiedDate", ""),
        last_modified_by=ws_data.get("lastModifiedUser", ws_data.get("lastModifiedBy", "")),
        created_date=ws_data.get("createdDate", ""),
        created_by=ws_data.get("createdUser", ws_data.get("createdBy", "")),
    )
