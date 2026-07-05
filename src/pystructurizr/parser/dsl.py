"""
Structurizr DSL parser.

Supports a subset of the Structurizr DSL spec:
  workspace / model / views blocks, person, softwareSystem, container,
  component elements, -> relationships, and systemContext/container/component views.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from pystructurizr.models import (
    AutomaticLayout,
    Component,
    Container,
    ContainerInstance,
    DeploymentNode,
    Enterprise,
    InfrastructureNode,
    Location,
    Person,
    RankDirection,
    Relationship,
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
EOF = _TT("EOF")


@dataclass
class Token:
    type: str
    value: str
    line: int


_TOKEN_RE = re.compile(
    r'(?P<COMMENT>//[^\n]*)|'
    r'(?P<BLOCK_COMMENT>/\*.*?\*/)|'
    r'(?P<STRING>"(?:[^"\\]|\\.)*")|'
    r'(?P<ARROW>->)|'
    r'(?P<EQUALS>=)|'
    r'(?P<LBRACE>\{)|'
    r'(?P<RBRACE>\})|'
    r'(?P<BANG>!)|'
    r'(?P<WILDCARD>\*)|'
    r'(?P<NEWLINE>\n)|'
    r'(?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)|'
    r'(?P<SKIP>[ \t\r]+)',
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

class ParseError(Exception):
    pass


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        # maps DSL identifier → element id used in Workspace
        self._id_map: dict[str, str] = {}
        self._rel_buffer: list[tuple[str, str, str, str]] = []

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, type_: str) -> Token:
        tok = self._advance()
        if tok.type != type_:
            raise ParseError(f"Line {tok.line}: expected {type_}, got {tok.type!r} ({tok.value!r})")
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
        for src, dst, desc, tech in self._rel_buffer:
            ws.relationships.append(
                Relationship(
                    source_id=self._id_map.get(src, src),
                    destination_id=self._id_map.get(dst, dst),
                    description=desc,
                    technology=tech,
                )
            )
        return ws

    def _parse_workspace(self) -> Workspace:
        self._expect_keyword("workspace")
        name = self._optional_string()
        description = self._optional_string()
        self._expect(LBRACE)

        ws = Workspace(name=name, description=description)

        while not self._match(RBRACE, EOF):
            kw = self._peek_value().lower()
            if kw == "model":
                self._parse_model(ws)
            elif kw == "views":
                self._parse_views(ws)
            elif kw == "configuration":
                self._skip_block()
            elif kw == "!identifiers":
                self._advance()  # consume keyword
                self._optional_ident()  # consume optional arg
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
            raise ParseError(f"Line {tok.line}: expected keyword '{kw}', got {tok.value!r}")

    def _parse_model(self, ws: Workspace) -> None:
        self._advance()  # consume 'model'
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            self._parse_model_item(ws, parent_id=None)
        self._expect(RBRACE)

    def _parse_model_item(self, ws: Workspace, parent_id: str | None) -> None:
        tok = self._peek()

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
            if kw in ("person", "softwaresystem", "container", "component",
                      "deploymentnode", "infrastructurenode",
                      "softwaresysteminstance", "containerinstance"):
                self._parse_element(ws, alias=None, parent_id=parent_id)
                return
            if kw == "enterprise":
                self._parse_enterprise(ws)
                return
            if kw == "group":
                self._parse_group(ws, parent_id)
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

    def _parse_element(self, ws: Workspace, alias: str | None, parent_id: str | None) -> None:
        kw = self._advance().value.lower()
        name = self._optional_string()
        description = self._optional_string()
        technology = self._optional_string() if kw in ("container", "component", "deploymentnode", "infrastructurenode") else ""
        tags_str = self._optional_string()
        tags = [t.strip() for t in tags_str.split(",")] if tags_str else []

        elem_id = alias or name.replace(" ", "_").lower()

        if kw == "person":
            location = Location.EXTERNAL if "External" in tags else Location.UNSPECIFIED
            elem = Person(id=elem_id, name=name, description=description, tags=tags, location=location)
            ws.people.append(elem)
            if alias:
                self._id_map[alias] = elem_id
        elif kw == "softwaresystem":
            location = Location.EXTERNAL if "External" in tags else Location.UNSPECIFIED
            elem = SoftwareSystem(id=elem_id, name=name, description=description, tags=tags, location=location)
            ws.software_systems.append(elem)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._parse_software_system_body(ws, elem)
        elif kw == "container":
            system = self._find_system(ws, parent_id)
            if system is not None:
                c = Container(id=elem_id, name=name, description=description, technology=technology, tags=tags, parent_id=system.id)
                system.containers.append(c)
                if alias:
                    self._id_map[alias] = elem_id
                if self._match(LBRACE):
                    self._parse_container_body(ws, c)
        elif kw == "component":
            container = self._find_container(ws, parent_id)
            if container is not None:
                comp = Component(id=elem_id, name=name, description=description, technology=technology, tags=tags, parent_id=container.id)
                container.components.append(comp)
                if alias:
                    self._id_map[alias] = elem_id
                if self._match(LBRACE):
                    self._skip_block()
        elif kw == "deploymentnode":
            parent_node = self._find_deployment_node(ws, parent_id)
            node = DeploymentNode(
                id=elem_id, name=name, description=description, technology=technology, tags=tags,
                parent_id=parent_node.id if parent_node is not None else "",
            )
            if parent_node is not None:
                parent_node.children.append(node)
            else:
                ws.deployment_nodes.append(node)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._parse_deployment_node_body(ws, node)
        elif kw == "infrastructurenode":
            parent_node = self._find_deployment_node(ws, parent_id)
            infra = InfrastructureNode(
                id=elem_id, name=name, description=description, technology=technology, tags=tags,
                parent_id=parent_node.id if parent_node is not None else "",
            )
            if parent_node is not None:
                parent_node.infrastructure_nodes.append(infra)
            if alias:
                self._id_map[alias] = elem_id
            if self._match(LBRACE):
                self._skip_block()
        elif kw == "softwaresysteminstance":
            system_id = self._id_map.get(name, name)
            inst = SoftwareSystemInstance(id=elem_id, software_system_id=system_id)
            parent_node = self._find_deployment_node(ws, parent_id)
            if parent_node is not None:
                parent_node.software_system_instances.append(inst)
            if alias:
                self._id_map[alias] = elem_id
        elif kw == "containerinstance":
            container_id = self._id_map.get(name, name)
            inst = ContainerInstance(id=elem_id, container_id=container_id)
            parent_node = self._find_deployment_node(ws, parent_id)
            if parent_node is not None:
                parent_node.container_instances.append(inst)
            if alias:
                self._id_map[alias] = elem_id

    def _parse_software_system_body(self, ws: Workspace, system: SoftwareSystem) -> None:
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            tok = self._peek()
            if tok.type == IDENT and tok.value.lower() == "container":
                if self._lookahead_is_equals():
                    alias = None
                    self._parse_model_item(ws, parent_id=system.id)
                else:
                    self._parse_model_item(ws, parent_id=system.id)
            elif tok.type == IDENT and self._lookahead_is_equals():
                # alias = container ...
                alias = self._advance().value
                self._expect(EQUALS)
                # peek at type
                if self._peek().value.lower() == "container":
                    self._parse_element(ws, alias=alias, parent_id=system.id)
                else:
                    self._advance()
            elif tok.type == IDENT and self._lookahead_is_arrow():
                self._parse_relationship()
            else:
                self._advance()
        self._expect(RBRACE)

    def _parse_container_body(self, ws: Workspace, container: Container) -> None:
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            tok = self._peek()
            if tok.type == IDENT and tok.value.lower() == "component":
                self._parse_model_item(ws, parent_id=container.id)
            elif tok.type == IDENT and self._lookahead_is_equals():
                alias = self._advance().value
                self._expect(EQUALS)
                if self._peek().value.lower() == "component":
                    self._parse_element(ws, alias=alias, parent_id=container.id)
                else:
                    self._advance()
            elif tok.type == IDENT and self._lookahead_is_arrow():
                self._parse_relationship()
            else:
                self._advance()
        self._expect(RBRACE)

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
        self._advance()  # consume 'group'
        self._optional_string()  # group name
        if self._match(LBRACE):
            self._expect(LBRACE)
            while not self._match(RBRACE, EOF):
                self._parse_model_item(ws, parent_id)
            self._expect(RBRACE)

    def _parse_deployment_node_body(self, ws: Workspace, node: DeploymentNode) -> None:
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            tok = self._peek()
            if tok.type == IDENT and self._lookahead_is_arrow():
                self._parse_relationship()
            elif tok.type == IDENT and self._lookahead_is_equals():
                alias = self._advance().value
                self._expect(EQUALS)
                self._parse_element(ws, alias=alias, parent_id=node.id)
            elif tok.type == IDENT:
                kw = tok.value.lower()
                if kw in ("deploymentnode", "infrastructurenode",
                          "softwaresysteminstance", "containerinstance"):
                    self._parse_element(ws, alias=None, parent_id=node.id)
                else:
                    self._advance()
            else:
                self._advance()
        self._expect(RBRACE)

    def _parse_relationship(self) -> None:
        src = self._advance().value
        # skip optional dot-notation (src.child -> ...)
        while self._match(IDENT) and self._peek_value() == ".":
            self._advance()
            if self._match(IDENT):
                self._advance()
        self._expect(ARROW)
        dst = self._advance().value
        description = self._optional_string()
        technology = self._optional_string()
        self._rel_buffer.append((src, dst, description, technology))
        # skip optional tags string and braces
        self._optional_string()
        if self._match(LBRACE):
            self._skip_block()

    def _parse_views(self, ws: Workspace) -> None:
        self._advance()  # consume 'views'
        self._expect(LBRACE)
        while not self._match(RBRACE, EOF):
            tok = self._peek()
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
            elif kw in ("filtered", "theme", "themes", "styles", "branding", "terminology"):
                self._advance()
                self._optional_string()
                if self._match(LBRACE):
                    self._skip_block()
            else:
                self._advance()
        self._expect(RBRACE)

    def _parse_view(self, view_type: ViewType) -> View:
        self._advance()  # consume keyword
        element_id = ""
        if self._match(IDENT):
            raw_id = self._advance().value
            element_id = self._id_map.get(raw_id, raw_id)
        key = ""
        if self._match(IDENT):
            key = self._advance().value
        elif self._match(STRING):
            key = self._advance().value.strip('"')
        title = self._optional_string()
        description = self._optional_string()
        view = View(type=view_type, key=key or element_id, element_id=element_id, title=title, description=description)
        if self._match(LBRACE):
            self._expect(LBRACE)
            while not self._match(RBRACE, EOF):
                self._parse_view_item(view)
            self._expect(RBRACE)
        return view

    def _parse_view_item(self, view: View) -> None:
        tok = self._peek()
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
                rank_dir = _RANK_DIRECTION_MAP.get(direction_str, RankDirection.TOP_BOTTOM)
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

    def _find_deployment_node(self, ws: Workspace, parent_id: str | None) -> DeploymentNode | None:
        if parent_id is None:
            return None
        return _search_deployment_nodes(ws.deployment_nodes, parent_id)

    def _find_system(self, ws: Workspace, parent_id: str | None) -> SoftwareSystem | None:
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


def _search_deployment_nodes(nodes: list[DeploymentNode], target_id: str) -> DeploymentNode | None:
    for node in nodes:
        if node.id == target_id:
            return node
        found = _search_deployment_nodes(node.children, target_id)
        if found is not None:
            return found
    return None


def parse_dsl(source: str) -> Workspace:
    """Parse a Structurizr DSL string and return a Workspace."""
    tokens = _tokenize(source)
    return _Parser(tokens).parse()


def parse_dsl_file(path: str | Path) -> Workspace:
    """Read a .dsl file and parse it."""
    return parse_dsl(Path(path).read_text(encoding="utf-8"))
