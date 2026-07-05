"""C4 model data classes representing the Structurizr metamodel."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums — element classification
# ---------------------------------------------------------------------------


class ElementType(str, Enum):
    PERSON = "person"
    SOFTWARE_SYSTEM = "softwareSystem"
    CONTAINER = "container"
    COMPONENT = "component"


class ViewType(str, Enum):
    SYSTEM_LANDSCAPE = "systemLandscape"
    SYSTEM_CONTEXT = "systemContext"
    CONTAINER = "container"
    COMPONENT = "component"
    DYNAMIC = "dynamic"
    DEPLOYMENT = "deployment"
    CUSTOM = "custom"
    IMAGE = "image"
    FILTERED = "filtered"


class Location(str, Enum):
    """Whether a Person or SoftwareSystem is internal or external to the enterprise."""

    INTERNAL = "Internal"
    EXTERNAL = "External"
    UNSPECIFIED = "Unspecified"


class InteractionStyle(str, Enum):
    SYNCHRONOUS = "Synchronous"
    ASYNCHRONOUS = "Asynchronous"


# ---------------------------------------------------------------------------
# Enums — layout
# ---------------------------------------------------------------------------


class RankDirection(str, Enum):
    TOP_BOTTOM = "TopBottom"
    BOTTOM_TOP = "BottomTop"
    LEFT_RIGHT = "LeftRight"
    RIGHT_LEFT = "RightLeft"


# ---------------------------------------------------------------------------
# Enums — styling
# ---------------------------------------------------------------------------


class Shape(str, Enum):
    BOX = "Box"
    ROUNDED_BOX = "RoundedBox"
    CIRCLE = "Circle"
    ELLIPSE = "Ellipse"
    HEXAGON = "Hexagon"
    DIAMOND = "Diamond"
    CYLINDER = "Cylinder"
    BUCKET = "Bucket"
    PIPE = "Pipe"
    PERSON = "Person"
    ROBOT = "Robot"
    FOLDER = "Folder"
    WEB_BROWSER = "WebBrowser"
    WINDOW = "Window"
    TERMINAL = "Terminal"
    SHELL = "Shell"
    MOBILE_DEVICE_PORTRAIT = "MobileDevicePortrait"
    MOBILE_DEVICE_LANDSCAPE = "MobileDeviceLandscape"
    COMPONENT = "Component"


class Routing(str, Enum):
    DIRECT = "Direct"
    CURVED = "Curved"
    ORTHOGONAL = "Orthogonal"


class LineStyle(str, Enum):
    DASHED = "Dashed"
    DOTTED = "Dotted"
    SOLID = "Solid"


class Border(str, Enum):
    SOLID = "Solid"
    DASHED = "Dashed"
    DOTTED = "Dotted"


class FilterMode(str, Enum):
    INCLUDE = "Include"
    EXCLUDE = "Exclude"


class ColorScheme(str, Enum):
    LIGHT = "Light"
    DARK = "Dark"


class IconPosition(str, Enum):
    TOP = "Top"
    BOTTOM = "Bottom"
    LEFT = "Left"


class ViewSortOrder(str, Enum):
    DEFAULT = "Default"
    TYPE = "Type"
    KEY = "Key"


class PaperSize(str, Enum):
    A6_PORTRAIT = "A6_Portrait"
    A6_LANDSCAPE = "A6_Landscape"
    A5_PORTRAIT = "A5_Portrait"
    A5_LANDSCAPE = "A5_Landscape"
    A4_PORTRAIT = "A4_Portrait"
    A4_LANDSCAPE = "A4_Landscape"
    A3_PORTRAIT = "A3_Portrait"
    A3_LANDSCAPE = "A3_Landscape"
    A2_PORTRAIT = "A2_Portrait"
    A2_LANDSCAPE = "A2_Landscape"
    A1_PORTRAIT = "A1_Portrait"
    A1_LANDSCAPE = "A1_Landscape"
    A0_PORTRAIT = "A0_Portrait"
    A0_LANDSCAPE = "A0_Landscape"
    LETTER_PORTRAIT = "Letter_Portrait"
    LETTER_LANDSCAPE = "Letter_Landscape"
    LEGAL_PORTRAIT = "Legal_Portrait"
    LEGAL_LANDSCAPE = "Legal_Landscape"
    SLIDE_4_3 = "Slide_4_3"
    SLIDE_16_9 = "Slide_16_9"
    SLIDE_16_10 = "Slide_16_10"


class Format(str, Enum):
    """Markup format for documentation sections and decisions."""

    MARKDOWN = "Markdown"
    ASCIIDOC = "AsciiDoc"


# ---------------------------------------------------------------------------
# Documentation value objects
# ---------------------------------------------------------------------------


@dataclass
class Section:
    """A section of long-form documentation attached to an element or workspace."""

    content: str = ""
    format: Format = Format.MARKDOWN
    title: str = ""
    filename: str = ""
    order: int = 0
    element_id: str = ""


@dataclass
class DecisionLink:
    """A link from one architecture decision to another."""

    id: str
    description: str = ""


@dataclass
class Decision:
    """An architecture decision record (ADR)."""

    id: str
    title: str = ""
    date: str = ""
    status: str = ""
    content: str = ""
    format: Format = Format.MARKDOWN
    element_id: str = ""
    links: list[DecisionLink] = field(default_factory=list)


@dataclass
class Image:
    """An image embedded in documentation."""

    name: str = ""
    content: str = ""
    type: str = ""


@dataclass
class Documentation:
    """A container for documentation sections, decisions, and images.

    Attached to a workspace or to a static-structure element
    (software system, container, or component).
    """

    sections: list[Section] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    images: list[Image] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Supporting value objects
# ---------------------------------------------------------------------------


@dataclass
class Perspective:
    """A named viewpoint on an element (e.g. security, performance)."""

    name: str
    description: str = ""
    value: str = ""
    url: str = ""
    title: str = ""


@dataclass
class Enterprise:
    """Named enterprise or organisation boundary shown on system landscape views."""

    name: str


@dataclass
class HttpHealthCheck:
    """HTTP health check endpoint on a deployed instance."""

    name: str
    url: str
    interval: int = 60
    timeout: int = 0
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class AutomaticLayout:
    """Automatic layout configuration for a view."""

    rank_direction: RankDirection = RankDirection.TOP_BOTTOM
    rank_separation: int = 100
    node_separation: int = 100
    edge_separation: int = 0
    vertices: bool = False


@dataclass
class Vertex:
    """A bend-point on a rendered relationship line."""

    x: int
    y: int


@dataclass
class Animation:
    """One step in an animated view."""

    order: int
    element_ids: list[str] = field(default_factory=list)
    relationship_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Relationship
# ---------------------------------------------------------------------------


@dataclass
class Relationship:
    """A directed relationship between two model elements."""

    source_id: str
    destination_id: str
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)
    id: str = ""
    interaction_style: InteractionStyle = InteractionStyle.SYNCHRONOUS
    linked_relationship_id: str = ""
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Static structure elements
# ---------------------------------------------------------------------------


@dataclass
class Component:
    """A component within a container."""

    id: str
    name: str
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    group: str = ""
    parent_id: str = ""
    documentation: Documentation = field(default_factory=Documentation)


@dataclass
class Container:
    """A container (application/datastore) within a software system."""

    id: str
    name: str
    description: str = ""
    technology: str = ""
    components: list[Component] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    group: str = ""
    parent_id: str = ""
    documentation: Documentation = field(default_factory=Documentation)


@dataclass
class SoftwareSystem:
    """A software system in the C4 model."""

    id: str
    name: str
    description: str = ""
    containers: list[Container] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    location: Location = Location.UNSPECIFIED
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    group: str = ""
    documentation: Documentation = field(default_factory=Documentation)


@dataclass
class Person:
    """A human actor (user or role) in the C4 model."""

    id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    location: Location = Location.UNSPECIFIED
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    group: str = ""


@dataclass
class CustomElement:
    """A user-defined element type."""

    id: str
    name: str
    description: str = ""
    metadata: str = ""
    tags: list[str] = field(default_factory=list)
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    group: str = ""
    icon: str = ""


# ---------------------------------------------------------------------------
# Deployment elements
# ---------------------------------------------------------------------------


@dataclass
class InfrastructureNode:
    """An infrastructure node within a deployment node (e.g. load balancer, firewall)."""

    id: str
    name: str
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    group: str = ""
    parent_id: str = ""
    icon: str = ""


@dataclass
class SoftwareSystemInstance:
    """A deployed instance of a SoftwareSystem within a DeploymentNode."""

    id: str
    software_system_id: str
    instance_id: int = 1
    environment: str = ""
    deployment_groups: list[str] = field(default_factory=list)
    health_checks: list[HttpHealthCheck] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)


@dataclass
class ContainerInstance:
    """A deployed instance of a Container within a DeploymentNode."""

    id: str
    container_id: str
    instance_id: int = 1
    environment: str = ""
    deployment_groups: list[str] = field(default_factory=list)
    health_checks: list[HttpHealthCheck] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)


@dataclass
class DeploymentNode:
    """Hierarchical deployment infrastructure node (e.g. AWS region, Kubernetes cluster, VM)."""

    id: str
    name: str
    description: str = ""
    technology: str = ""
    instances: int = 1
    environment: str = ""
    tags: list[str] = field(default_factory=list)
    url: str = ""
    properties: dict[str, str] = field(default_factory=dict)
    perspectives: list[Perspective] = field(default_factory=list)
    group: str = ""
    parent_id: str = ""
    icon: str = ""
    children: list[DeploymentNode] = field(default_factory=list)
    infrastructure_nodes: list[InfrastructureNode] = field(default_factory=list)
    software_system_instances: list[SoftwareSystemInstance] = field(
        default_factory=list
    )
    container_instances: list[ContainerInstance] = field(default_factory=list)
    deployment_groups: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# View models
# ---------------------------------------------------------------------------


@dataclass
class ViewElement:
    """An element included in a view with optional x/y position."""

    id: str
    x: Optional[int] = None
    y: Optional[int] = None
    title: str = ""
    description: str = ""
    width: Optional[int] = None
    height: Optional[int] = None


@dataclass
class RelationshipView:
    """A relationship included in a view, with optional rendering metadata."""

    id: str
    description: str = ""
    url: str = ""
    order: str = ""
    response: Optional[bool] = None
    vertices: list[Vertex] = field(default_factory=list)
    routing: Optional[Routing] = None
    jump: Optional[bool] = None
    position: Optional[int] = None
    properties: dict[str, str] = field(default_factory=dict)
    title: str = ""
    link: Optional[bool] = None
    link_element: Optional[int] = None


@dataclass
class View:
    """A view (diagram) in the workspace."""

    type: ViewType
    key: str
    element_id: str = ""
    title: str = ""
    description: str = ""
    include_all: bool = False
    included_ids: list[str] = field(default_factory=list)
    excluded_ids: list[str] = field(default_factory=list)
    auto_layout: Optional[AutomaticLayout] = None
    order: int = 0
    properties: dict[str, str] = field(default_factory=dict)
    paper_size: Optional[PaperSize] = None
    relationship_views: list[RelationshipView] = field(default_factory=list)
    element_views: list[ViewElement] = field(default_factory=list)
    animations: list[Animation] = field(default_factory=list)
    owner: str = ""
    disable_automatic_layout: bool = False
    hide_element_metadata: bool = False
    hide_relationship_metadata: bool = False
    # Deployment / dynamic views
    environment: str = ""
    external_boundaries_visible: bool = False
    # Filtered views
    base_view_key: str = ""
    filter_mode: Optional[FilterMode] = None
    filter_tags: list[str] = field(default_factory=list)
    # Image views
    content: str = ""
    content_light: str = ""
    content_dark: str = ""
    content_type: str = ""


# ---------------------------------------------------------------------------
# Styling models
# ---------------------------------------------------------------------------


@dataclass
class ElementStyle:
    """Styling rule applied to elements whose tags match."""

    tag: str
    width: Optional[int] = None
    height: Optional[int] = None
    background: str = ""
    stroke: str = ""
    stroke_width: Optional[int] = None
    color: str = ""
    font_size: Optional[int] = None
    shape: Optional[Shape] = None
    icon: str = ""
    border: Optional[Border] = None
    opacity: Optional[int] = None
    metadata: Optional[bool] = None
    description: Optional[bool] = None
    color_scheme: Optional[ColorScheme] = None
    icon_position: Optional[IconPosition] = None


@dataclass
class RelationshipStyle:
    """Styling rule applied to relationships whose tags match."""

    tag: str
    thickness: Optional[int] = None
    color: str = ""
    font_size: Optional[int] = None
    width: Optional[int] = None
    dashed: Optional[bool] = None
    style: Optional[LineStyle] = None
    routing: Optional[Routing] = None
    jump: Optional[bool] = None
    position: Optional[int] = None
    opacity: Optional[int] = None
    metadata: Optional[bool] = None
    description: Optional[bool] = None
    color_scheme: Optional[ColorScheme] = None


@dataclass
class Styles:
    """Collection of element and relationship styling rules."""

    element_styles: list[ElementStyle] = field(default_factory=list)
    relationship_styles: list[RelationshipStyle] = field(default_factory=list)


@dataclass
class Terminology:
    """Custom label overrides for each element type."""

    enterprise: str = "Enterprise"
    person: str = "Person"
    software_system: str = "Software System"
    container: str = "Container"
    component: str = "Component"
    code: str = "Code"
    deployment_node: str = "Deployment Node"
    infrastructure_node: str = "Infrastructure Node"
    relationship: str = "Relationship"


@dataclass
class Branding:
    """Custom branding configuration: brand color, font, and logo URL."""

    color: str = ""
    font: str = ""
    logo: str = ""


@dataclass
class Configuration:
    """Workspace view configuration: styles, themes, and terminology."""

    styles: Styles = field(default_factory=Styles)
    themes: list[str] = field(default_factory=list)
    terminology: Terminology = field(default_factory=Terminology)
    default_view: str = ""
    last_saved_view: str = ""
    metadata_symbols: str = ""
    view_sort_order: Optional[ViewSortOrder] = None
    properties: dict[str, str] = field(default_factory=dict)
    branding: Optional[Branding] = None
    generators_and_exporters: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Model — static structure container
# ---------------------------------------------------------------------------


@dataclass
class Model:
    """Static C4 model: all elements and relationships in the workspace."""

    people: list[Person] = field(default_factory=list)
    software_systems: list[SoftwareSystem] = field(default_factory=list)
    custom_elements: list[CustomElement] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    deployment_nodes: list[DeploymentNode] = field(default_factory=list)
    deployment_environments: list[str] = field(default_factory=list)
    enterprise: Optional[Enterprise] = None
    properties: dict[str, str] = field(default_factory=dict)

    def find_element(
        self, element_id: str
    ) -> (
        Person
        | SoftwareSystem
        | Container
        | Component
        | DeploymentNode
        | InfrastructureNode
        | CustomElement
        | None
    ):
        """Look up any element by id across all levels of the model."""
        for p in self.people:
            if p.id == element_id:
                return p
        for ce in self.custom_elements:
            if ce.id == element_id:
                return ce
        for s in self.software_systems:
            if s.id == element_id:
                return s
            for c in s.containers:
                if c.id == element_id:
                    return c
                for comp in c.components:
                    if comp.id == element_id:
                        return comp
        for dn in self.deployment_nodes:
            result = _find_in_deployment_node(dn, element_id)
            if result is not None:
                return result
        return None

    def all_relationships_for(self, ids: set[str]) -> list[Relationship]:
        """Return relationships where both source and destination are in ids."""
        return [
            r
            for r in self.relationships
            if r.source_id in ids and r.destination_id in ids
        ]


# ---------------------------------------------------------------------------
# ViewSet — typed view collection with list-protocol back-compat
# ---------------------------------------------------------------------------


_VIEW_TYPE_TO_ATTR: dict[ViewType, str] = {
    ViewType.SYSTEM_LANDSCAPE: "system_landscape_views",
    ViewType.SYSTEM_CONTEXT: "system_context_views",
    ViewType.CONTAINER: "container_views",
    ViewType.COMPONENT: "component_views",
    ViewType.DYNAMIC: "dynamic_views",
    ViewType.DEPLOYMENT: "deployment_views",
    ViewType.CUSTOM: "custom_views",
    ViewType.IMAGE: "image_views",
    ViewType.FILTERED: "filtered_views",
}


@dataclass
class ViewSet:
    """All views, grouped by type. Supports list-like access for legacy callers."""

    system_landscape_views: list[View] = field(default_factory=list)
    system_context_views: list[View] = field(default_factory=list)
    container_views: list[View] = field(default_factory=list)
    component_views: list[View] = field(default_factory=list)
    dynamic_views: list[View] = field(default_factory=list)
    deployment_views: list[View] = field(default_factory=list)
    custom_views: list[View] = field(default_factory=list)
    image_views: list[View] = field(default_factory=list)
    filtered_views: list[View] = field(default_factory=list)
    configuration: Configuration = field(default_factory=Configuration)

    def get_all_views(self) -> list[View]:
        """Return every view across all types, in declaration order."""
        return [
            *self.system_landscape_views,
            *self.system_context_views,
            *self.container_views,
            *self.component_views,
            *self.dynamic_views,
            *self.deployment_views,
            *self.custom_views,
            *self.image_views,
            *self.filtered_views,
        ]

    def append(self, view: View) -> None:
        """Append a view to the typed list matching its view.type."""
        attr = _VIEW_TYPE_TO_ATTR.get(view.type)
        if attr is None:
            return
        target: list[View] = getattr(self, attr)
        target.append(view)

    def __iter__(self) -> Iterator[View]:
        return iter(self.get_all_views())

    def __len__(self) -> int:
        return (
            len(self.system_landscape_views)
            + len(self.system_context_views)
            + len(self.container_views)
            + len(self.component_views)
            + len(self.dynamic_views)
            + len(self.deployment_views)
            + len(self.custom_views)
            + len(self.image_views)
            + len(self.filtered_views)
        )

    def __getitem__(self, index: int) -> View:
        return self.get_all_views()[index]


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------


@dataclass
class Workspace:
    """Root container for an entire Structurizr model."""

    name: str
    description: str = ""
    model: Model = field(default_factory=Model)
    views: ViewSet = field(default_factory=ViewSet)
    id: str = ""
    version: int = 1
    revision: int = 1
    last_modified_date: str = ""
    last_modified_by: str = ""
    created_date: str = ""
    created_by: str = ""
    documentation: Documentation = field(default_factory=Documentation)

    @property
    def people(self) -> list[Person]:
        return self.model.people

    @property
    def custom_elements(self) -> list[CustomElement]:
        return self.model.custom_elements

    @property
    def software_systems(self) -> list[SoftwareSystem]:
        return self.model.software_systems

    @property
    def relationships(self) -> list[Relationship]:
        return self.model.relationships

    @property
    def deployment_nodes(self) -> list[DeploymentNode]:
        return self.model.deployment_nodes

    @property
    def deployment_environments(self) -> list[str]:
        return self.model.deployment_environments

    @property
    def enterprise(self) -> Optional[Enterprise]:
        return self.model.enterprise

    @enterprise.setter
    def enterprise(self, value: Optional[Enterprise]) -> None:
        self.model.enterprise = value

    @property
    def configuration(self) -> Configuration:
        return self.views.configuration

    @configuration.setter
    def configuration(self, value: Configuration) -> None:
        self.views.configuration = value

    def find_element(
        self, element_id: str
    ) -> (
        Person
        | SoftwareSystem
        | Container
        | Component
        | DeploymentNode
        | InfrastructureNode
        | CustomElement
        | None
    ):
        return self.model.find_element(element_id)

    def all_relationships_for(self, ids: set[str]) -> list[Relationship]:
        return self.model.all_relationships_for(ids)

    def validate(self) -> list[str]:
        """Return a list of validation issues; empty list means the workspace is well-formed.

        Checks:
        - View keys must be non-empty.
        - View keys must be unique across the workspace.
        """
        issues: list[str] = []
        seen: dict[str, int] = {}
        for view in self.views:
            if not view.key:
                issues.append(f"View of type {view.type.value} has an empty key.")
                continue
            seen[view.key] = seen.get(view.key, 0) + 1
        for key, count in seen.items():
            if count > 1:
                issues.append(f"Duplicate view key {key!r} appears {count} times.")
        return issues


def _find_in_deployment_node(
    node: DeploymentNode, element_id: str
) -> DeploymentNode | InfrastructureNode | None:
    """Recursively search a deployment node subtree for an element by id."""
    if node.id == element_id:
        return node
    for infra in node.infrastructure_nodes:
        if infra.id == element_id:
            return infra
    for child in node.children:
        result = _find_in_deployment_node(child, element_id)
        if result is not None:
            return result
    return None
