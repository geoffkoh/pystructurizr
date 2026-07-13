"""
Mermaid C4 diagram generator.

Converts a Workspace + View into Mermaid C4 syntax, supporting:
  - C4Context  (system context views)
  - C4Container (container views)
  - C4Component (component views)
"""

from __future__ import annotations

from pystructurizr.models import (
    Container,
    Location,
    Relationship,
    View,
    ViewType,
    Workspace,
)


def _safe_id(raw: str) -> str:
    """Convert an element id into a valid Mermaid node id."""
    return raw.replace("-", "_").replace(" ", "_")


def _q(text: str) -> str:
    return text.replace('"', '\\"')


class MermaidGenerator:
    """Generate Mermaid C4 diagrams from a Workspace."""

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def generate_all(self) -> dict[str, str]:
        """Return a mapping of view key → mermaid diagram string."""
        return {v.key: self.generate_view(v) for v in self.workspace.views}

    def generate_view(self, view: View) -> str:
        if view.type == ViewType.SYSTEM_CONTEXT:
            return self._system_context(view)
        if view.type == ViewType.CONTAINER:
            return self._container(view)
        if view.type == ViewType.COMPONENT:
            return self._component(view)
        return f"%%  View type {view.type} is not yet supported\n"

    # ------------------------------------------------------------------
    # System Context
    # ------------------------------------------------------------------

    def _system_context(self, view: View) -> str:
        ws = self.workspace
        lines: list[str] = ["C4Context"]
        title = view.title or f"System Context – {view.element_id}"
        lines.append(f"    title {_q(title)}")
        lines.append("")

        visible_ids = self._visible_ids(view)
        grouped: dict[str, list[str]] = {}

        for person in ws.people:
            if person.id in visible_ids:
                tag = "Person_Ext" if person.location == Location.EXTERNAL else "Person"
                entity = f'{tag}({_safe_id(person.id)}, "{_q(person.name)}", "{_q(person.description)}")'
                self._emit(lines, grouped, entity, person.group)

        for system in ws.software_systems:
            if system.id in visible_ids:
                tag = "System_Ext" if system.location == Location.EXTERNAL else "System"
                entity = f'{tag}({_safe_id(system.id)}, "{_q(system.name)}", "{_q(system.description)}")'
                self._emit(lines, grouped, entity, system.group)

        self._append_group_boundaries(lines, grouped, indent="    ")

        lines.append("")
        for rel in ws.all_relationships_for(visible_ids):
            self._append_rel(lines, rel)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Container
    # ------------------------------------------------------------------

    def _container(self, view: View) -> str:
        ws = self.workspace
        lines: list[str] = ["C4Container"]
        subject = ws.find_element(view.element_id)
        subject_name = subject.name if subject else view.element_id
        title = view.title or f"Container Diagram – {subject_name}"
        lines.append(f"    title {_q(title)}")
        lines.append("")

        visible_ids = self._visible_ids(view)

        for person in ws.people:
            if person.id in visible_ids:
                tag = "Person_Ext" if person.location == Location.EXTERNAL else "Person"
                lines.append(
                    f'    {tag}({_safe_id(person.id)}, "{_q(person.name)}", "{_q(person.description)}")'
                )

        for system in ws.software_systems:
            if system.id == view.element_id:
                lines.append(
                    f'    System_Boundary({_safe_id(system.id)}, "{_q(system.name)}") {{'
                )
                grouped: dict[str, list[str]] = {}
                for container in system.containers:
                    if container.id in visible_ids or view.include_all:
                        tech = (
                            f", {_q(container.technology)}"
                            if container.technology
                            else ', ""'
                        )
                        entity = f'Container({_safe_id(container.id)}, "{_q(container.name)}"{tech}, "{_q(container.description)}")'
                        self._emit(
                            lines, grouped, entity, container.group, indent="        "
                        )
                self._append_group_boundaries(lines, grouped, indent="        ")
                lines.append("    }")
            elif system.id in visible_ids and system.id != view.element_id:
                tag = "System_Ext" if system.location == Location.EXTERNAL else "System"
                lines.append(
                    f'    {tag}({_safe_id(system.id)}, "{_q(system.name)}", "{_q(system.description)}")'
                )

        lines.append("")
        all_ids: set[str] = set()
        for system in ws.software_systems:
            if system.id == view.element_id:
                all_ids.update(c.id for c in system.containers)
        all_ids.update(visible_ids)
        for rel in ws.all_relationships_for(all_ids):
            self._append_rel(lines, rel)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Component
    # ------------------------------------------------------------------

    def _component(self, view: View) -> str:
        ws = self.workspace
        lines: list[str] = ["C4Component"]
        subject = ws.find_element(view.element_id)
        subject_name = subject.name if subject else view.element_id
        title = view.title or f"Component Diagram – {subject_name}"
        lines.append(f"    title {_q(title)}")
        lines.append("")

        visible_ids = self._visible_ids(view)

        # find the container
        container: Container | None = None
        for system in ws.software_systems:
            for c in system.containers:
                if c.id == view.element_id:
                    container = c
                    break

        if container:
            lines.append(
                f'    Container_Boundary({_safe_id(container.id)}, "{_q(container.name)}") {{'
            )
            grouped: dict[str, list[str]] = {}
            for comp in container.components:
                if comp.id in visible_ids or view.include_all:
                    tech = f", {_q(comp.technology)}" if comp.technology else ', ""'
                    entity = f'Component({_safe_id(comp.id)}, "{_q(comp.name)}"{tech}, "{_q(comp.description)}")'
                    self._emit(lines, grouped, entity, comp.group, indent="        ")
            self._append_group_boundaries(lines, grouped, indent="        ")
            lines.append("    }")

        # external containers / people
        for person in ws.people:
            if person.id in visible_ids:
                tag = "Person_Ext" if person.location == Location.EXTERNAL else "Person"
                lines.append(
                    f'    {tag}({_safe_id(person.id)}, "{_q(person.name)}", "{_q(person.description)}")'
                )
        for system in ws.software_systems:
            for c in system.containers:
                if c.id in visible_ids and (container is None or c.id != container.id):
                    tech = f", {_q(c.technology)}" if c.technology else ', ""'
                    lines.append(
                        f'    Container_Ext({_safe_id(c.id)}, "{_q(c.name)}"{tech}, "{_q(c.description)}")'
                    )

        lines.append("")
        all_ids: set[str] = set(visible_ids)
        if container:
            all_ids.update(comp.id for comp in container.components)
        for rel in ws.all_relationships_for(all_ids):
            self._append_rel(lines, rel)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        lines: list[str],
        grouped: dict[str, list[str]],
        entity: str,
        group: str,
        indent: str = "    ",
    ) -> None:
        """Append an entity line, deferring grouped ones for boundary blocks."""
        if group:
            grouped.setdefault(group, []).append(entity)
        else:
            lines.append(indent + entity)

    def _append_group_boundaries(
        self, lines: list[str], grouped: dict[str, list[str]], indent: str
    ) -> None:
        """Emit one ``Boundary`` block per model group path.

        Nested group paths (``a/b``) render as a single boundary labelled
        with the last path segment; the boundary id embeds the full path.
        """
        for path, entities in grouped.items():
            gid = _safe_id("group_" + path.replace("/", "_"))
            label = path.split("/")[-1]
            lines.append(f'{indent}Boundary({gid}, "{_q(label)}") {{')
            lines.extend(f"{indent}    {entity}" for entity in entities)
            lines.append(f"{indent}}}")

    def _append_rel(self, lines: list[str], rel: Relationship) -> None:
        tech = f', "{_q(rel.technology)}"' if rel.technology else ""
        lines.append(
            f'    Rel({_safe_id(rel.source_id)}, {_safe_id(rel.destination_id)}, "{_q(rel.description)}"{tech})'
        )

    def _visible_ids(self, view: View) -> set[str]:
        if view.include_all:
            ws = self.workspace
            ids: set[str] = set()
            ids.update(p.id for p in ws.people)
            ids.update(s.id for s in ws.software_systems)
            for s in ws.software_systems:
                ids.update(c.id for c in s.containers)
                for c in s.containers:
                    ids.update(comp.id for comp in c.components)
            ids.difference_update(view.excluded_ids)
            return ids
        if view.included_ids:
            return set(view.included_ids) - set(view.excluded_ids)
        # default: include everything reachable for this view
        return self._default_visible(view)

    def _default_visible(self, view: View) -> set[str]:
        ws = self.workspace
        ids: set[str] = set()
        if view.type == ViewType.SYSTEM_CONTEXT:
            ids.update(p.id for p in ws.people)
            ids.update(s.id for s in ws.software_systems)
        elif view.type == ViewType.CONTAINER:
            ids.update(p.id for p in ws.people)
            ids.update(s.id for s in ws.software_systems)
            for s in ws.software_systems:
                if s.id == view.element_id:
                    ids.update(c.id for c in s.containers)
        elif view.type == ViewType.COMPONENT:
            for s in ws.software_systems:
                for c in s.containers:
                    if c.id == view.element_id:
                        ids.update(comp.id for comp in c.components)
                    else:
                        ids.add(c.id)
            ids.update(p.id for p in ws.people)
        return ids
