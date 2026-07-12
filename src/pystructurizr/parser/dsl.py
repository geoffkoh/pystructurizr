"""
Structurizr DSL parser.

Supports a subset of the Structurizr DSL spec:
  workspace / model / views blocks, person, softwareSystem, container,
  component elements, -> relationships, and systemContext/container/component views.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pystructurizr.parser.docs import load_decisions, load_sections, markdown_files
from pystructurizr.models import (
    AutomaticLayout,
    Border,
    Component,
    Container,
    ContainerInstance,
    CustomElement,
    DeploymentNode,
    ElementStyle,
    Enterprise,
    FilterMode,
    HttpHealthCheck,
    InfrastructureNode,
    Location,
    Person,
    Perspective,
    RankDirection,
    Relationship,
    RelationshipStyle,
    RelationshipView,
    Shape,
    SoftwareSystem,
    SoftwareSystemInstance,
    View,
    ViewType,
    Workspace,
)


# ---------------------------------------------------------------------------
# Tokeniser
# ---------------------------------------------------------------------------


class TokenType(str):
    pass


_TT = TokenType

IDENT = _TT("IDENT")
STRING = _TT("STRING")
LBRACE = _TT("LBRACE")
RBRACE = _TT("RBRACE")
ARROW = _TT("ARROW")
EQUALS = _TT("EQUALS")
BANG = _TT("BANG")
WILDCARD = _TT("WILDCARD")
COLOR = _TT("COLOR")
NUMBER = _TT("NUMBER")
EOF = _TT("EOF")


@dataclass
class Token:
    type: str
    value: str
    line: int


_TOKEN_RE = re.compile(
    r"(?P<COMMENT>//[^\n]*)|"
    r"(?P<BLOCK_COMMENT>/\*.*?\*/)|"
    r'(?P<STRING>"(?:[^"\\]|\\.)*")|'
    r"(?P<ARROW>->)|"
    r"(?P<EQUALS>=)|"
    r"(?P<LBRACE>\{)|"
    r"(?P<RBRACE>\})|"
    r"(?P<BANG>!)|"
    r"(?P<WILDCARD>\*)|"
    r"(?P<NEWLINE>\n)|"
    r"(?P<COLOR>#[0-9A-Fa-f]{3,8})|"
    r"(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)|"
    r"(?P<NUMBER>[0-9]+)|"
    r"(?P<SKIP>[ \t\r]+)",
    re.DOTALL,
)


def _tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    for m in _TOKEN_RE.finditer(text):
        kind = m.lastgroup
        value = m.group()
        if kind in ("COMMENT", "BLOCK_COMMENT", "NEWLINE", "SKIP"):
            if "\n" in value:
                line += value.count("\n")
            continue
        tokens.append(Token(kind, value, line))  # type: ignore[arg-type]
    tokens.append(Token(EOF, "", line))
    return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


_SHAPE_MAP = {shape.value.lower(): shape for shape in Shape}
_BORDER_MAP = {border.value.lower(): border for border in Border}

# Child-element keywords allowed inside each element kind's body.
_CHILD_KEYWORDS: dict[str, tuple[str, ...]] = {
    "softwaresystem": ("container",),
    "container": ("component",),
    "deploymentnode": (
        "deploymentnode",
        "infrastructurenode",
        "softwaresysteminstance",
        "containerinstance",
    ),
}


class ParseError(Exception):
    pass


class UnsupportedFeatureWarning(UserWarning):
    """Warning issued when the DSL uses a feature the parser ignores."""


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        # maps DSL identifier → element id used in Workspace
        self._id_map: dict[str, str] = {}
        # relationships whose source/destination hold raw DSL identifiers
        # until the whole model has been parsed
        self._rel_buffer: list[Relationship] = []
        self._warnings: list[str] = []
        # active deploymentEnvironment name while parsing its block
        self._current_environment: str = ""
        # active group names while parsing nested group blocks
        self._group_stack: list[str] = []
        # deploymentGroup declarations: alias/name → group name
        self._deployment_groups: dict[str, str] = {}

    @property
    def _current_group(self) -> str:
        return "/".join(g for g in self._group_stack if g)

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, type_: str) -> Token:
        tok = self._advance()
        if tok.type != type_:
            raise ParseError(
                f"Line {tok.line}: expected {type_}, got {tok.type!r} ({tok.value!r})"
            )
        return tok

    def _match(self, *types: str) -> bool:
        return self._peek().type in types

    def _peek_value(self) -> str:
        return self._peek().value

    def _optional_string(self) -> str:
        if self._match(STRING):
            return self._advance().value.strip('"')
        return ""

    def _parse_string(self) -> str:
        return self._expect(STRING).value.strip('"')

    def parse(self) -> Workspace:
        ws = self._parse_workspace()
        # resolve buffered relationships
        for rel in self._rel_buffer:
            rel.source_id = self._id_map.get(rel.source_id, rel.source_id)
            rel.destination_id = self._id_map.get(
                rel.destination_id, rel.destination_id
            )
            ws.relationships.append(rel)
        ws.parse_warnings = self._warnings
        return ws

    def _parse_workspace(self) -> Workspace:
        self._expect_keyword("workspace")
        name = self._optional_string()
        description = self._optional_string()
        self._expect(LBRACE)

        ws = Workspace(name=name, description=description)

        while not self._match(RBRACE, EOF):
            if self._match(BANG):
                self._parse_directive("workspace")
                continue
            kw = self._peek_value().lower()
            if kw == "model":
                self._parse_model(ws)
            elif kw == "views":
                self._parse_views(ws)
            elif kw == "configuration":
                self._advance()
                if self._match(LBRACE):
                    self._skip_block()
            else:
                self._advance()

        if self._match(RBRACE):
            self._advance()
        return ws

    def _optional_ident(self) -> str:
        if self._match(IDENT):
            return self._advance().value
        return ""

    def _idents_on_line(self, line: int) -> list[str]:
        """Consume identifiers that remain on ``line``, resolved to element ids.

        Used for view ``include``/``exclude`` statements, which may name
        several elements on one line; identifiers on later lines belong to
        the next view statement.
        """
        resolved: list[str] = []
        while self._match(IDENT) and self._peek().line == line:
            raw = self._advance().value
            resolved.append(self._id_map.get(raw, raw))
        return resolved

    def _expect_keyword(self, kw: str) -> None:
        tok = self._advance()
        if tok.type != IDENT or tok.value.lower() != kw:
            raise ParseError(
                f"Line {tok.line}: expected keyword '{kw}', got {tok.value!r}"
            )

    def _parse_directive(self, scope: str) -> None:
        """Parse a ``!directive`` encountered at the given scope.

        Known directives dispatch to a ``_directive_<name>`` method; unknown
        ones are skipped (their same-line arguments plus any ``{...}`` block)
        and recorded as an unsupported-feature warning.
        """
        self._expect(BANG)
        if not self._match(IDENT):
            return
        name_tok = self._advance()
        handler = getattr(self, f"_directive_{name_tok.value.lower()}", None)
        if handler is not None:
            handler(scope, name_tok.line)
            return
        while (
            self._match(IDENT, STRING, NUMBER, COLOR, WILDCARD, EQUALS)
            and self._peek().line == name_tok.line
        ):
            self._advance()
        if self._match(LBRACE):
            self._skip_block()
        self._warn(
            f"Line {name_tok.line}: unsupported directive '!{name_tok.value}' ignored"
        )

    def _directive_identifiers(self, scope: str, line: int) -> None:
        # hierarchical|flat — identifier scoping is not yet implemented;
        # flat resolution applies regardless of the requested mode.
        if self._match(IDENT) and self._peek().line == line:
            self._advance()

    def _warn(self, message: str) -> None:
        self._warnings.append(message)
        warnings.warn(message, UnsupportedFeatureWarning, stacklevel=2)

    def _parse_model(self, ws: Workspace) -> None:
        self._advance()  # consume 'model'
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            self._parse_model_item(ws, parent_id=None)
        self._expect(RBRACE)

    def _parse_model_item(self, ws: Workspace, parent_id: str | None) -> None:
        tok = self._peek()

        if tok.type == BANG:
            self._parse_directive("model")
            return

        # relationship: source -> dest ...
        if tok.type == IDENT and self._lookahead_is_arrow():
            self._parse_relationship()
            return

        # assignment: identifier = element_type ...
        if tok.type == IDENT and self._lookahead_is_equals():
            alias = self._advance().value
            self._expect(EQUALS)
            self._parse_element(ws, alias, parent_id)
            return

        # keyword elements without alias
        if tok.type == IDENT:
            kw = tok.value.lower()
            if kw in (
                "person",
                "softwaresystem",
                "container",
                "component",
                "deploymentnode",
                "infrastructurenode",
                "softwaresysteminstance",
                "containerinstance",
                "deploymentgroup",
                "element",
            ):
                self._parse_element(ws, alias=None, parent_id=parent_id)
                return
            if kw == "enterprise":
                self._parse_enterprise(ws)
                return
            if kw == "group":
                self._parse_group(ws, parent_id)
                return
            if kw == "deploymentenvironment":
                self._parse_deployment_environment(ws)
                return

        # skip unknown token
        self._advance()

    def _lookahead_is_arrow(self) -> bool:
        i = self._pos + 1
        while i < len(self._tokens) and self._tokens[i].type in (IDENT, STRING):
            i += 1
        return i < len(self._tokens) and self._tokens[i].type == ARROW

    def _lookahead_is_equals(self) -> bool:
        return (
            self._pos + 1 < len(self._tokens)
            and self._tokens[self._pos + 1].type == EQUALS
        )

    def _parse_element(
        self, ws: Workspace, alias: str | None, parent_id: str | None
    ) -> None:
        kw_tok = self._advance()
        kw = kw_tok.value.lower()
        if kw in ("softwaresysteminstance", "containerinstance"):
            self._parse_instance(ws, kw, alias, parent_id, kw_tok.line)
            return
        name = self._optional_string()
        # element <name> [metadata] [description] [tags] — custom elements
        # take a metadata string before the description.
        metadata = self._optional_string() if kw == "element" else ""
        description = self._optional_string()
        technology = (
            self._optional_string()
            if kw in ("container", "component", "deploymentnode", "infrastructurenode")
            else ""
        )
        tags_str = self._optional_string()
        tags = [t.strip() for t in tags_str.split(",")] if tags_str else []

        # deploymentNode <name> [description] [technology] [tags] [instances]
        instances = 1
        if kw == "deploymentnode":
            if self._match(NUMBER):
                instances = int(self._advance().value)
            elif self._match(STRING):
                raw = self._advance().value.strip('"')
                if raw.isdigit():
                    instances = int(raw)  # ranges like "0..N" keep the default

        elem_id = alias or name.replace(" ", "_").lower()

        if kw == "person":
            location = Location.EXTERNAL if "External" in tags else Location.UNSPECIFIED
            elem = Person(
                id=elem_id,
                name=name,
                description=description,
                tags=tags,
                location=location,
                group=self._current_group,
            )
            ws.people.append(elem)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._parse_element_body(ws, elem, "person")
        elif kw == "softwaresystem":
            location = Location.EXTERNAL if "External" in tags else Location.UNSPECIFIED
            sys_elem = SoftwareSystem(
                id=elem_id,
                name=name,
                description=description,
                tags=tags,
                location=location,
                group=self._current_group,
            )
            ws.software_systems.append(sys_elem)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._parse_element_body(ws, sys_elem, "softwaresystem")
        elif kw == "container":
            system = self._find_system(ws, parent_id)
            if system is not None:
                c = Container(
                    id=elem_id,
                    name=name,
                    description=description,
                    technology=technology,
                    tags=tags,
                    parent_id=system.id,
                    group=self._current_group,
                )
                system.containers.append(c)
                if alias:
                    self._id_map[alias] = elem_id
                if self._match(LBRACE):
                    self._parse_element_body(ws, c, "container")
        elif kw == "component":
            container = self._find_container(ws, parent_id)
            if container is not None:
                comp = Component(
                    id=elem_id,
                    name=name,
                    description=description,
                    technology=technology,
                    tags=tags,
                    parent_id=container.id,
                    group=self._current_group,
                )
                container.components.append(comp)
                if alias:
                    self._id_map[alias] = elem_id
                if self._match(LBRACE):
                    self._parse_element_body(ws, comp, "component")
        elif kw == "deploymentnode":
            parent_node = self._find_deployment_node(ws, parent_id)
            node = DeploymentNode(
                id=elem_id,
                name=name,
                description=description,
                technology=technology,
                instances=instances,
                tags=tags,
                environment=self._current_environment,
                parent_id=parent_node.id if parent_node is not None else "",
                group=self._current_group,
            )
            if parent_node is not None:
                parent_node.children.append(node)
            else:
                ws.deployment_nodes.append(node)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._parse_element_body(ws, node, "deploymentnode")
        elif kw == "infrastructurenode":
            parent_node = self._find_deployment_node(ws, parent_id)
            infra = InfrastructureNode(
                id=elem_id,
                name=name,
                description=description,
                technology=technology,
                tags=tags,
                parent_id=parent_node.id if parent_node is not None else "",
                group=self._current_group,
            )
            if parent_node is not None:
                parent_node.infrastructure_nodes.append(infra)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._parse_element_body(ws, infra, "infrastructurenode")
        elif kw == "deploymentgroup":
            # deploymentGroup declarations only feed the parser registry;
            # membership is recorded on instances, not the workspace.
            if name:
                self._deployment_groups[name] = name
                if alias:
                    self._deployment_groups[alias] = name
        elif kw == "element":
            custom = CustomElement(
                id=elem_id,
                name=name,
                metadata=metadata,
                description=description,
                tags=tags,
                group=self._current_group,
            )
            ws.model.custom_elements.append(custom)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._parse_element_body(ws, custom, "element")

    def _parse_instance(
        self,
        ws: Workspace,
        kw: str,
        alias: str | None,
        parent_id: str | None,
        line: int,
    ) -> None:
        """Parse ``softwareSystemInstance``/``containerInstance``.

        Syntax: ``<keyword> <identifier> [deploymentGroups] [tags]`` — a
        positional argument whose comma-separated items all name declared
        deployment groups is the group list; anything else is tags.
        """
        ref = ""
        if self._match(IDENT) and self._peek().line == line:
            ref = self._advance().value
        elif self._match(STRING) and self._peek().line == line:
            ref = self._advance().value.strip('"')

        deployment_groups: list[str] = []
        tags: list[str] = []
        while self._match(STRING, IDENT) and self._peek().line == line:
            raw = self._advance().value.strip('"')
            items = [t.strip() for t in raw.split(",") if t.strip()]
            if items and all(item in self._deployment_groups for item in items):
                deployment_groups.extend(self._deployment_groups[i] for i in items)
            else:
                tags.extend(items)

        target_id = self._id_map.get(ref, ref)
        inst_id = alias or self._unique_id(f"{target_id}_instance")
        parent_node = self._find_deployment_node(ws, parent_id)
        if kw == "softwaresysteminstance":
            inst = SoftwareSystemInstance(
                id=inst_id,
                software_system_id=target_id,
                environment=self._current_environment,
                deployment_groups=deployment_groups,
                tags=tags,
            )
            if parent_node is not None:
                parent_node.software_system_instances.append(inst)
            self._id_map[alias or inst_id] = inst_id
            if self._match(LBRACE):
                self._parse_element_body(ws, inst, kw)
        else:
            cont_inst = ContainerInstance(
                id=inst_id,
                container_id=target_id,
                environment=self._current_environment,
                deployment_groups=deployment_groups,
                tags=tags,
            )
            if parent_node is not None:
                parent_node.container_instances.append(cont_inst)
            self._id_map[alias or inst_id] = inst_id
            if self._match(LBRACE):
                self._parse_element_body(ws, cont_inst, kw)

    def _parse_element_body(self, ws: Workspace, element: Any, kind: str) -> None:
        """Parse the ``{ ... }`` body shared by every element kind.

        Handles the metadata keywords common to all elements, relationships,
        directives, ``group`` blocks, and the child-element keywords valid
        for ``kind``; anything else is skipped.
        """
        self._expect(LBRACE)
        children = _CHILD_KEYWORDS.get(kind, ())
        # Group context does not cross parent boundaries: a container of a
        # grouped system is not itself in the group (structurizr-java).
        saved_groups = self._group_stack
        self._group_stack = []
        while not self._match(RBRACE, EOF):
            tok = self._peek()
            if tok.type == BANG:
                self._parse_directive("element")
                continue
            if tok.type == ARROW or (tok.type == IDENT and self._lookahead_is_arrow()):
                self._parse_relationship(this_id=element.id)
                continue
            if tok.type == IDENT and self._lookahead_is_equals():
                alias = self._advance().value
                self._expect(EQUALS)
                if self._peek().value.lower() in children:
                    self._parse_element(ws, alias=alias, parent_id=element.id)
                else:
                    self._advance()
                continue
            if tok.type == IDENT:
                kw = tok.value.lower()
                if kw in children:
                    self._parse_element(ws, alias=None, parent_id=element.id)
                    continue
                if kw == "group":
                    self._parse_group(ws, element.id)
                    continue
                if self._parse_common_element_keyword(element, kw):
                    continue
            self._advance()
        self._expect(RBRACE)
        self._group_stack = saved_groups

    def _parse_common_element_keyword(self, element: Any, kw: str) -> bool:
        """Handle a metadata keyword valid on any element; True if handled."""
        if kw == "description" and hasattr(element, "description"):
            self._advance()
            element.description = self._optional_string()
            return True
        if kw == "technology" and hasattr(element, "technology"):
            self._advance()
            element.technology = self._optional_string()
            return True
        if kw == "url" and hasattr(element, "url"):
            self._advance()
            # URLs must be quoted (the tokenizer has no unquoted-URL token)
            element.url = self._optional_string()
            return True
        if kw in ("tag", "tags") and hasattr(element, "tags"):
            line = self._advance().line
            while self._match(STRING) and self._peek().line == line:
                raw = self._advance().value.strip('"')
                element.tags.extend(t.strip() for t in raw.split(",") if t.strip())
            return True
        if kw == "properties" and hasattr(element, "properties"):
            self._advance()
            element.properties.update(self._parse_properties_block())
            return True
        if kw == "perspectives" and hasattr(element, "perspectives"):
            self._advance()
            element.perspectives.extend(self._parse_perspectives_block())
            return True
        if kw == "healthcheck" and hasattr(element, "health_checks"):
            # healthCheck <name> <url> [interval] [timeout]
            self._advance()
            check = HttpHealthCheck(
                name=self._optional_string(), url=self._optional_string()
            )
            if self._match(NUMBER):
                check.interval = int(self._advance().value)
            if self._match(NUMBER):
                check.timeout = int(self._advance().value)
            element.health_checks.append(check)
            return True
        return False

    def _parse_properties_block(self) -> dict[str, str]:
        """Parse ``{ <name> <value> ... }`` name/value pairs, one per line."""
        props: dict[str, str] = {}
        if not self._match(LBRACE):
            return props
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            if not self._match(STRING, IDENT, NUMBER, COLOR):
                self._advance()
                continue
            tok = self._advance()
            name = tok.value.strip('"')
            value = ""
            if (
                self._match(STRING, IDENT, NUMBER, COLOR)
                and self._peek().line == tok.line
            ):
                value = self._advance().value.strip('"')
            # extra tokens on the same line are ignored
            while (
                self._match(STRING, IDENT, NUMBER, COLOR)
                and self._peek().line == tok.line
            ):
                self._advance()
            props[name] = value
        self._expect(RBRACE)
        return props

    def _parse_perspectives_block(self) -> list[Perspective]:
        """Parse ``{ <name> <description> [value] ... }`` lines."""
        perspectives: list[Perspective] = []
        if not self._match(LBRACE):
            return perspectives
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            if not self._match(STRING, IDENT):
                self._advance()
                continue
            tok = self._advance()
            values = [tok.value.strip('"')]
            while self._match(STRING, IDENT) and self._peek().line == tok.line:
                values.append(self._advance().value.strip('"'))
            perspectives.append(
                Perspective(
                    name=values[0],
                    description=values[1] if len(values) > 1 else "",
                    value=values[2] if len(values) > 2 else "",
                )
            )
        self._expect(RBRACE)
        return perspectives

    def _parse_enterprise(self, ws: Workspace) -> None:
        self._advance()  # consume 'enterprise'
        name = self._optional_string()
        ws.enterprise = Enterprise(name=name)
        if self._match(LBRACE):
            self._expect(LBRACE)
            while not self._match(RBRACE, EOF):
                self._parse_model_item(ws, parent_id=None)
            self._expect(RBRACE)

    def _parse_group(self, ws: Workspace, parent_id: str | None) -> None:
        """Parse ``group "Name" { ... }``; members record the group path.

        Nested group paths join with ``/`` and set the
        ``structurizr.groupSeparator`` model property, matching
        structurizr-java.
        """
        self._advance()  # consume 'group'
        name = self._optional_string()
        self._group_stack.append(name)
        if len(self._group_stack) > 1:
            ws.model.properties.setdefault("structurizr.groupSeparator", "/")
        if self._match(LBRACE):
            self._expect(LBRACE)
            while not self._match(RBRACE, EOF):
                self._parse_model_item(ws, parent_id)
            self._expect(RBRACE)
        self._group_stack.pop()

    def _parse_deployment_environment(self, ws: Workspace) -> None:
        """Parse ``deploymentEnvironment "Name" { ... }``.

        Deployment nodes and instances created inside the block are stamped
        with the environment name so deployment views can filter on it.
        """
        self._advance()  # consume keyword
        env_name = self._optional_string() or self._optional_ident()
        if env_name and env_name not in ws.model.deployment_environments:
            ws.model.deployment_environments.append(env_name)
        previous = self._current_environment
        self._current_environment = env_name
        if self._match(LBRACE):
            self._expect(LBRACE)
            while not self._match(RBRACE, EOF):
                self._parse_model_item(ws, parent_id=None)
            self._expect(RBRACE)
        self._current_environment = previous

    def _unique_id(self, base: str) -> str:
        """Return ``base`` or a numbered variant not yet used as an id."""
        taken = set(self._id_map.values())
        if base not in taken:
            return base
        n = 2
        while f"{base}_{n}" in taken:
            n += 1
        return f"{base}_{n}"

    def _parse_relationship(self, this_id: str | None = None) -> None:
        if self._match(ARROW):
            # implicit source: `-> dst ...` inside an element body
            self._advance()
            src = this_id or ""
        else:
            src = self._advance().value
            self._expect(ARROW)
        dst = self._advance().value
        if this_id is not None:
            if src.lower() == "this":
                src = this_id
            if dst.lower() == "this":
                dst = this_id
        description = self._optional_string()
        technology = self._optional_string()
        # source/destination hold raw DSL identifiers; parse() resolves them
        # once the whole model is known.
        rel = Relationship(
            source_id=src,
            destination_id=dst,
            description=description,
            technology=technology,
        )
        tags_str = self._optional_string()
        if tags_str:
            rel.tags.extend(t.strip() for t in tags_str.split(",") if t.strip())
        if self._match(LBRACE):
            self._parse_relationship_body(rel)
        self._rel_buffer.append(rel)

    def _parse_relationship_body(self, rel: Relationship) -> None:
        """Parse a relationship's nested block: tags, url, properties, perspectives."""
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            if not self._match(IDENT):
                self._advance()
                continue
            kw = self._peek_value().lower()
            if kw in ("tag", "tags"):
                line = self._advance().line
                while self._match(STRING) and self._peek().line == line:
                    raw = self._advance().value.strip('"')
                    rel.tags.extend(t.strip() for t in raw.split(",") if t.strip())
            elif kw == "url":
                self._advance()
                rel.url = self._optional_string()
            elif kw == "properties":
                self._advance()
                rel.properties.update(self._parse_properties_block())
            elif kw == "perspectives":
                self._advance()
                rel.perspectives.extend(self._parse_perspectives_block())
            else:
                self._advance()
        self._expect(RBRACE)

    def _parse_views(self, ws: Workspace) -> None:
        self._advance()  # consume 'views'
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            tok = self._peek()
            if tok.type == BANG:
                self._parse_directive("views")
                continue
            if tok.type != IDENT:
                self._advance()
                continue
            kw = tok.value.lower()
            if kw == "systemlandscape":
                ws.views.append(self._parse_view(ViewType.SYSTEM_LANDSCAPE))
            elif kw == "systemcontext":
                ws.views.append(self._parse_view(ViewType.SYSTEM_CONTEXT))
            elif kw == "container":
                ws.views.append(self._parse_view(ViewType.CONTAINER))
            elif kw == "component":
                ws.views.append(self._parse_view(ViewType.COMPONENT))
            elif kw == "dynamic":
                ws.views.append(self._parse_view(ViewType.DYNAMIC))
            elif kw == "deployment":
                ws.views.append(self._parse_view(ViewType.DEPLOYMENT))
            elif kw == "styles":
                self._parse_styles(ws)
            elif kw in ("theme", "themes"):
                # theme "url" / themes "url" "url" ... — URLs must be quoted
                # (the tokenizer has no token for unquoted ://... runs).
                self._advance()
                while self._match(STRING):
                    url = self._advance().value.strip('"')
                    if url:
                        ws.views.configuration.themes.append(url)
            elif kw == "filtered":
                ws.views.append(self._parse_filtered_view())
            elif kw in ("branding", "terminology"):
                self._advance()
                self._optional_string()
                if self._match(LBRACE):
                    self._skip_block()
            else:
                self._advance()
        self._expect(RBRACE)

    def _parse_styles(self, ws: Workspace) -> None:
        """Parse a views-level ``styles`` block into the view configuration.

        Supports ``element "Tag" { ... }`` and ``relationship "Tag" { ... }``
        rules; unknown rule kinds and properties are skipped.
        """
        self._advance()  # consume 'styles'
        if not self._match(LBRACE):
            return
        self._expect(LBRACE)
        styles = ws.views.configuration.styles
        while not self._match(RBRACE, EOF):
            kw = self._peek_value().lower() if self._match(IDENT) else ""
            if kw == "element":
                self._advance()
                style = ElementStyle(tag=self._optional_string())
                self._parse_element_style_body(style)
                styles.element_styles.append(style)
            elif kw == "relationship":
                self._advance()
                rel_style = RelationshipStyle(tag=self._optional_string())
                self._parse_relationship_style_body(rel_style)
                styles.relationship_styles.append(rel_style)
            else:
                self._advance()
        self._expect(RBRACE)

    def _style_value(self) -> str:
        """Consume and return one style property value token, if present."""
        if self._match(COLOR, STRING):
            return self._advance().value.strip('"')
        if self._match(IDENT, NUMBER):
            return self._advance().value
        return ""

    def _parse_element_style_body(self, style: ElementStyle) -> None:
        if not self._match(LBRACE):
            return
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            if not self._match(IDENT):
                self._advance()
                continue
            prop = self._advance().value.lower()
            value = self._style_value()
            if prop == "background":
                style.background = value
            elif prop in ("color", "colour"):
                style.color = value
            elif prop == "stroke":
                style.stroke = value
            elif prop == "shape":
                style.shape = _SHAPE_MAP.get(value.lower())
            elif prop == "border":
                style.border = _BORDER_MAP.get(value.lower())
            elif prop == "icon":
                style.icon = value
            elif prop == "fontsize" and value.isdigit():
                style.font_size = int(value)
            elif prop == "opacity" and value.isdigit():
                style.opacity = int(value)
            elif prop == "width" and value.isdigit():
                style.width = int(value)
            elif prop == "height" and value.isdigit():
                style.height = int(value)
            # Unknown properties: the value token is consumed; ignore.
        self._expect(RBRACE)

    def _parse_relationship_style_body(self, style: RelationshipStyle) -> None:
        if not self._match(LBRACE):
            return
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            if not self._match(IDENT):
                self._advance()
                continue
            prop = self._advance().value.lower()
            value = self._style_value()
            if prop in ("color", "colour"):
                style.color = value
            elif prop == "thickness" and value.isdigit():
                style.thickness = int(value)
            elif prop == "width" and value.isdigit():
                style.width = int(value)
            elif prop == "fontsize" and value.isdigit():
                style.font_size = int(value)
            elif prop == "dashed":
                style.dashed = value.lower() == "true"
        self._expect(RBRACE)

    def _parse_view(self, view_type: ViewType) -> View:
        self._advance()  # consume keyword
        element_id = ""
        if view_type == ViewType.SYSTEM_LANDSCAPE:
            pass  # landscape views are unscoped; the first token is the key
        elif self._match(WILDCARD):
            self._advance()  # deployment scope "*" means unscoped
        elif self._match(IDENT):
            raw_id = self._advance().value
            element_id = self._id_map.get(raw_id, raw_id)
        environment = ""
        if view_type == ViewType.DEPLOYMENT:
            # deployment <scope> <environment> [key] [title] [description]
            if self._match(STRING):
                environment = self._advance().value.strip('"')
            elif self._match(IDENT):
                environment = self._advance().value
        key = ""
        if self._match(IDENT):
            key = self._advance().value
        elif self._match(STRING):
            key = self._advance().value.strip('"')
        title = self._optional_string()
        description = self._optional_string()
        view = View(
            type=view_type,
            key=key or element_id or environment,
            element_id=element_id,
            title=title,
            description=description,
            environment=environment,
        )
        if self._match(LBRACE):
            self._expect(LBRACE)
            while not self._match(RBRACE, EOF):
                self._parse_view_item(view)
            self._expect(RBRACE)
        return view

    def _parse_filtered_view(self) -> View:
        """Parse ``filtered <baseKey> <include|exclude> <tags> [key] [title]``.

        Tags may be a single identifier or a quoted comma-separated list.
        """
        self._advance()  # consume 'filtered'
        base_key = ""
        if self._match(IDENT):
            base_key = self._advance().value
        elif self._match(STRING):
            base_key = self._advance().value.strip('"')

        mode = FilterMode.INCLUDE
        if self._match(IDENT):
            raw_mode = self._advance().value.lower()
            if raw_mode == "exclude":
                mode = FilterMode.EXCLUDE

        tags: list[str] = []
        if self._match(STRING):
            raw_tags = self._advance().value.strip('"')
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        elif self._match(IDENT):
            tags = [self._advance().value]

        key = ""
        if self._match(IDENT):
            key = self._advance().value
        elif self._match(STRING):
            key = self._advance().value.strip('"')
        title = self._optional_string()
        description = self._optional_string()
        if self._match(LBRACE):
            self._skip_block()

        return View(
            type=ViewType.FILTERED,
            key=key or f"{base_key}_{mode.value.lower()}",
            title=title,
            description=description,
            base_view_key=base_key,
            filter_mode=mode,
            filter_tags=tags,
        )

    def _parse_view_item(self, view: View) -> None:
        tok = self._peek()
        if tok.type == BANG:
            self._parse_directive("view")
            return
        # Dynamic views list ordered interaction steps: `a -> b "description"`.
        # Steps are stored as RelationshipViews whose id encodes the
        # endpoints (`src__dst`) and whose order is the 1-based step number.
        if (
            view.type == ViewType.DYNAMIC
            and tok.type == IDENT
            and self._lookahead_is_arrow()
        ):
            raw_src = self._advance().value
            self._expect(ARROW)
            raw_dst = self._expect(IDENT).value
            description = self._optional_string()
            self._optional_string()  # optional technology, not stored
            if self._match(LBRACE):
                self._skip_block()  # step metadata block, not stored
            src = self._id_map.get(raw_src, raw_src)
            dst = self._id_map.get(raw_dst, raw_dst)
            view.relationship_views.append(
                RelationshipView(
                    id=f"{src}__{dst}",
                    description=description,
                    order=str(len(view.relationship_views) + 1),
                )
            )
            return
        if tok.type == IDENT:
            kw = tok.value.lower()
            if kw == "include":
                line = self._advance().line
                if self._match(WILDCARD):
                    self._advance()
                    view.include_all = True
                else:
                    view.included_ids.extend(self._idents_on_line(line))
                return
            if kw == "exclude":
                line = self._advance().line
                view.excluded_ids.extend(self._idents_on_line(line))
                return
            if kw == "autolayout":
                self._advance()
                direction_str = self._optional_ident().lower()
                _RANK_DIRECTION_MAP = {
                    "tb": RankDirection.TOP_BOTTOM,
                    "bt": RankDirection.BOTTOM_TOP,
                    "lr": RankDirection.LEFT_RIGHT,
                    "rl": RankDirection.RIGHT_LEFT,
                    "topbottom": RankDirection.TOP_BOTTOM,
                    "bottomtop": RankDirection.BOTTOM_TOP,
                    "leftright": RankDirection.LEFT_RIGHT,
                    "rightleft": RankDirection.RIGHT_LEFT,
                }
                rank_dir = _RANK_DIRECTION_MAP.get(
                    direction_str, RankDirection.TOP_BOTTOM
                )
                self._optional_string()  # rank separation (ignored for now)
                view.auto_layout = AutomaticLayout(rank_direction=rank_dir)
                return
            if kw == "title":
                self._advance()
                view.title = self._optional_string()
                return
            if kw == "description":
                self._advance()
                view.description = self._optional_string()
                return
            if kw == "animation":
                self._advance()
                if self._match(LBRACE):
                    self._skip_block()
                return
        self._advance()

    def _skip_block(self) -> None:
        self._expect(LBRACE)
        depth = 1
        while depth > 0 and not self._match(EOF):
            tok = self._advance()
            if tok.type == LBRACE:
                depth += 1
            elif tok.type == RBRACE:
                depth -= 1

    def _find_deployment_node(
        self, ws: Workspace, parent_id: str | None
    ) -> DeploymentNode | None:
        if parent_id is None:
            return None
        return _search_deployment_nodes(ws.deployment_nodes, parent_id)

    def _find_system(
        self, ws: Workspace, parent_id: str | None
    ) -> SoftwareSystem | None:
        if parent_id is None:
            return None
        for s in ws.software_systems:
            if s.id == parent_id:
                return s
        return None

    def _find_container(self, ws: Workspace, parent_id: str | None) -> Container | None:
        if parent_id is None:
            return None
        for s in ws.software_systems:
            for c in s.containers:
                if c.id == parent_id:
                    return c
        return None


def _search_deployment_nodes(
    nodes: list[DeploymentNode], target_id: str
) -> DeploymentNode | None:
    for node in nodes:
        if node.id == target_id:
            return node
        found = _search_deployment_nodes(node.children, target_id)
        if found is not None:
            return found
    return None


# ---------------------------------------------------------------------------
# !include preprocessing
# ---------------------------------------------------------------------------

_INCLUDE_RE = re.compile(
    r'^[ \t]*!include[ \t]+(?P<target>"[^"]+"|\S+)[ \t]*$', re.MULTILINE
)

_DOCS_RE = re.compile(
    r'^[ \t]*!(?P<kind>docs|adrs)[ \t]+(?P<target>"[^"]+"|\S+)[ \t]*$',
    re.MULTILINE,
)


def _expand_includes(
    source: str, base_dir: Path | None, stack: tuple[Path, ...]
) -> str:
    """Replace ``!include <path>`` lines with the referenced file contents.

    Paths are resolved relative to the including file's directory and may
    themselves contain further includes. Used before tokenising so the
    parser only ever sees a single flattened source.

    Args:
        source: DSL text possibly containing ``!include`` lines.
        base_dir: Directory relative paths resolve against; ``None`` when
            parsing a bare string, in which case any ``!include`` is an
            error.
        stack: Chain of files already being expanded, for cycle detection.

    Raises:
        ParseError: If there is no file context, the target does not exist,
            or the includes form a cycle.
    """

    def replace(match: re.Match[str]) -> str:
        target = match.group("target").strip('"')
        if base_dir is None:
            raise ParseError(
                f"!include {target!r} requires a file context; "
                "parse from a file instead of a string"
            )
        included = (base_dir / target).resolve()
        if included in stack:
            chain = " -> ".join(str(p) for p in (*stack, included))
            raise ParseError(f"Circular !include: {chain}")
        if not included.is_file():
            raise ParseError(f"!include target not found: {included}")
        text = included.read_text(encoding="utf-8")
        return _expand_includes(text, included.parent, (*stack, included))

    return _INCLUDE_RE.sub(replace, source)


def parse_dsl(source: str, base_dir: str | Path | None = None) -> Workspace:
    """Parse a Structurizr DSL string and return a Workspace.

    Args:
        source: The DSL text.
        base_dir: Directory that ``!include``, ``!docs`` and ``!adrs``
            paths resolve against (directives in included fragments resolve
            against the root file's directory). When ``None`` (parsing a
            bare string), any of these directives raises
            :class:`ParseError`.
    """
    resolved = Path(base_dir).resolve() if base_dir is not None else None
    flattened = _expand_includes(source, resolved, ())

    doc_dirs: list[tuple[str, Path]] = []

    def extract_docs(match: re.Match[str]) -> str:
        target = match.group("target").strip('"')
        if resolved is None:
            raise ParseError(
                f"!{match.group('kind')} {target!r} requires a file context; "
                "parse from a file instead of a string"
            )
        doc_dirs.append((match.group("kind"), (resolved / target).resolve()))
        return ""

    flattened = _DOCS_RE.sub(extract_docs, flattened)
    tokens = _tokenize(flattened)
    workspace = _Parser(tokens).parse()

    for kind, directory in doc_dirs:
        if kind == "docs":
            workspace.documentation.sections.extend(load_sections(directory))
        else:
            workspace.documentation.decisions.extend(load_decisions(directory))
    return workspace


def parse_dsl_file(path: str | Path) -> Workspace:
    """Read a .dsl file and parse it, resolving any ``!include`` directives."""
    path = Path(path).resolve()
    return parse_dsl(path.read_text(encoding="utf-8"), base_dir=path.parent)


def collect_source_files(path: str | Path) -> list[Path]:
    """Return ``path`` plus every file it (transitively) ``!include``s.

    Best-effort: unreadable or missing include targets are skipped and
    cycles are ignored, so this is safe to call on sources that would fail
    to parse. Used by the web app to know which files to watch for
    live-reload.
    """
    root = Path(path).resolve()
    seen: set[Path] = set()
    ordered: list[Path] = []

    def visit(current: Path) -> None:
        if current in seen:
            return
        seen.add(current)
        ordered.append(current)
        try:
            text = current.read_text(encoding="utf-8")
        except OSError:
            return
        for match in _INCLUDE_RE.finditer(text):
            target = match.group("target").strip('"')
            included = (current.parent / target).resolve()
            if included.is_file():
                visit(included)
        for match in _DOCS_RE.finditer(text):
            target = match.group("target").strip('"')
            directory = (root.parent / target).resolve()
            for doc in markdown_files(directory):
                if doc not in seen:
                    seen.add(doc)
                    ordered.append(doc)

    visit(root)
    return ordered
