"""Tests for the g6_view graph-data helper reused by the web app."""

from __future__ import annotations

from pathlib import Path

import pytest

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
from pystructurizr.parser.dsl import parse_dsl_file
from pystructurizr.webapp.g6_view import apply_positions, to_g6_data

FIXTURE = Path(__file__).parent.parent / "fixtures" / "example.dsl"


def _view(workspace: Workspace, view_type: ViewType) -> View:
    for view in workspace.views:
        if view.type == view_type:
            return view
    raise AssertionError(f"fixture has no {view_type} view")


def _node_by_label(data: dict, label: str) -> dict:
    for node in data["nodes"]:
        if node["data"]["label"] == label:
            return node
    raise AssertionError(f"no node labelled {label!r}")


def _edge_pairs(data: dict) -> set[tuple[str, str]]:
    return {(e["source"], e["target"]) for e in data["edges"]}


@pytest.fixture
def workspace() -> Workspace:
    return parse_dsl_file(FIXTURE)


class TestSystemContextView:
    def test_shows_only_people_and_systems(self, workspace: Workspace) -> None:
        data = to_g6_data(workspace, _view(workspace, ViewType.SYSTEM_CONTEXT))
        kinds = {n["data"]["kind"] for n in data["nodes"]}
        assert "container" not in kinds
        assert "component" not in kinds
        labels = {n["data"]["label"] for n in data["nodes"]}
        assert labels == {
            "Personal Banking Customer",
            "Internet Banking System",
            "E-mail System",
            "Mainframe Banking System",
        }

    def test_lifts_container_relationships_to_the_system(
        self, workspace: Workspace
    ) -> None:
        data = to_g6_data(workspace, _view(workspace, ViewType.SYSTEM_CONTEXT))
        customer = _node_by_label(data, "Personal Banking Customer")["id"]
        bank = _node_by_label(data, "Internet Banking System")["id"]
        email = _node_by_label(data, "E-mail System")["id"]
        pairs = _edge_pairs(data)
        # customer -> spa/webapp lift to a single customer -> bank edge.
        assert (customer, bank) in pairs
        # api -> email lifts to bank -> email.
        assert (bank, email) in pairs
        # No self edges from intra-system relationships (webapp -> spa etc.).
        assert (bank, bank) not in pairs

    def test_has_no_boundary_node(self, workspace: Workspace) -> None:
        data = to_g6_data(workspace, _view(workspace, ViewType.SYSTEM_CONTEXT))
        assert all(n["data"]["kind"] != "boundary" for n in data["nodes"])


class TestContainerView:
    def test_scoped_system_becomes_the_boundary(self, workspace: Workspace) -> None:
        view = _view(workspace, ViewType.CONTAINER)
        data = to_g6_data(workspace, view)
        boundary = data["nodes"][0]
        assert boundary["data"]["kind"] == "boundary"
        assert boundary["id"] == view.element_id
        # The scoped system must not also appear as a leaf node.
        leaves = [n for n in data["nodes"][1:] if n["id"] == view.element_id]
        assert leaves == []

    def test_containers_are_nested_in_the_boundary(self, workspace: Workspace) -> None:
        view = _view(workspace, ViewType.CONTAINER)
        data = to_g6_data(workspace, view)
        containers = [n for n in data["nodes"] if n["data"]["kind"] == "container"]
        assert len(containers) == 4
        assert all(n["parentId"] == view.element_id for n in containers)

    def test_external_elements_stay_outside_the_boundary(
        self, workspace: Workspace
    ) -> None:
        data = to_g6_data(workspace, _view(workspace, ViewType.CONTAINER))
        outside = [
            n
            for n in data["nodes"]
            if n["data"]["kind"] in {"person", "system-external"}
        ]
        assert len(outside) == 3  # customer, email, mainframe
        assert all("parentId" not in n for n in outside)

    def test_edges_connect_leaves_across_the_boundary(
        self, workspace: Workspace
    ) -> None:
        data = to_g6_data(workspace, _view(workspace, ViewType.CONTAINER))
        api = _node_by_label(data, "API Application")["id"]
        email = _node_by_label(data, "E-mail System")["id"]
        pairs = _edge_pairs(data)
        assert (api, email) in pairs

    def test_nodes_carry_technology_and_description(self, workspace: Workspace) -> None:
        data = to_g6_data(workspace, _view(workspace, ViewType.CONTAINER))
        webapp = _node_by_label(data, "Web Application")
        assert webapp["data"]["technology"] == "Java, Spring MVC"
        assert webapp["data"]["description"] == "Serves static content"


class TestComponentView:
    @pytest.fixture
    def component_workspace(self) -> Workspace:
        """A workspace with components, built in code (fixture DSL has none)."""
        ws = Workspace(name="Shop")
        ctrl = Component(id="ctrl", name="Order Controller", technology="Spring MVC")
        svc = Component(id="svc", name="Order Service")
        api = Container(id="api", name="API", components=[ctrl, svc])
        db = Container(id="db", name="Database", technology="PostgreSQL")
        unrelated = Container(id="cache", name="Cache")
        ws.model.software_systems.append(
            SoftwareSystem(id="shop", name="Shop", containers=[api, db, unrelated])
        )
        ws.model.software_systems.append(
            SoftwareSystem(id="pay", name="Payment Provider")
        )
        ws.model.people.append(Person(id="user", name="Customer"))
        ws.model.relationships.extend(
            [
                Relationship(source_id="user", destination_id="ctrl", id="r1"),
                Relationship(source_id="ctrl", destination_id="svc", id="r2"),
                Relationship(source_id="svc", destination_id="db", id="r3"),
                Relationship(source_id="svc", destination_id="pay", id="r4"),
            ]
        )
        ws.views.append(
            View(type=ViewType.COMPONENT, key="components", element_id="api")
        )
        return ws

    def test_scoped_container_becomes_the_boundary(
        self, component_workspace: Workspace
    ) -> None:
        view = component_workspace.views[0]
        data = to_g6_data(component_workspace, view)
        boundary = data["nodes"][0]
        assert boundary["data"]["kind"] == "boundary"
        assert boundary["id"] == "api"

    def test_components_nest_and_related_peers_show(
        self, component_workspace: Workspace
    ) -> None:
        data = to_g6_data(component_workspace, component_workspace.views[0])
        by_id = {n["id"]: n for n in data["nodes"]}
        assert by_id["ctrl"]["parentId"] == "api"
        assert by_id["svc"]["parentId"] == "api"
        # Related sibling container, external system and person are outside.
        assert "parentId" not in by_id["db"]
        assert "pay" in by_id
        assert "user" in by_id
        # The unrelated sibling container and parent system are not shown.
        assert "cache" not in by_id
        assert "shop" not in by_id

    def test_cross_boundary_edges_survive(self, component_workspace: Workspace) -> None:
        data = to_g6_data(component_workspace, component_workspace.views[0])
        pairs = _edge_pairs(data)
        assert pairs == {
            ("user", "ctrl"),
            ("ctrl", "svc"),
            ("svc", "db"),
            ("svc", "pay"),
        }


def test_apply_positions_round_trip(workspace: Workspace) -> None:
    view = workspace.views[0]
    # Pick two visible node ids from the generated graph so the test does
    # not depend on the specific identifiers in the fixture.
    ids = [n["id"] for n in to_g6_data(workspace, view)["nodes"]][:2]
    assert len(ids) == 2

    apply_positions(view, {ids[0]: (100, 200), ids[1]: (300, 400)})
    assert len(view.element_views) == 2

    data = to_g6_data(workspace, view)
    positioned = {
        node["id"]: node["style"]
        for node in data["nodes"]
        if "style" in node and "x" in node["style"]
    }
    assert positioned[ids[0]] == {"x": 100, "y": 200}
    assert positioned[ids[1]] == {"x": 300, "y": 400}
