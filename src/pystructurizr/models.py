"""C4 model data classes representing the Structurizr metamodel."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ElementType(str, Enum):
    PERSON = "person"
    SOFTWARE_SYSTEM = "softwareSystem"
    CONTAINER = "container"
    COMPONENT = "component"


class ViewType(str, Enum):
    SYSTEM_CONTEXT = "systemContext"
    CONTAINER = "container"
    COMPONENT = "component"
    DYNAMIC = "dynamic"
    DEPLOYMENT = "deployment"


@dataclass
class Relationship:
    source_id: str
    destination_id: str
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Component:
    id: str
    name: str
    description: str = ""
    technology: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Container:
    id: str
    name: str
    description: str = ""
    technology: str = ""
    components: list[Component] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class SoftwareSystem:
    id: str
    name: str
    description: str = ""
    containers: list[Container] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    external: bool = False


@dataclass
class Person:
    id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    external: bool = False


@dataclass
class ViewElement:
    """An element included in a view, with optional x/y position."""
    id: str
    x: Optional[int] = None
    y: Optional[int] = None


@dataclass
class View:
    type: ViewType
    key: str
    element_id: str = ""
    title: str = ""
    description: str = ""
    include_all: bool = False
    included_ids: list[str] = field(default_factory=list)
    excluded_ids: list[str] = field(default_factory=list)
    auto_layout: bool = False


@dataclass
class Workspace:
    name: str
    description: str = ""
    people: list[Person] = field(default_factory=list)
    software_systems: list[SoftwareSystem] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    views: list[View] = field(default_factory=list)

    def find_element(self, element_id: str) -> Person | SoftwareSystem | Container | Component | None:
        """Look up any element by id across all levels."""
        for p in self.people:
            if p.id == element_id:
                return p
        for s in self.software_systems:
            if s.id == element_id:
                return s
            for c in s.containers:
                if c.id == element_id:
                    return c
                for comp in c.components:
                    if comp.id == element_id:
                        return comp
        return None

    def all_relationships_for(self, ids: set[str]) -> list[Relationship]:
        """Return relationships where both source and destination are in ids."""
        return [r for r in self.relationships if r.source_id in ids and r.destination_id in ids]
