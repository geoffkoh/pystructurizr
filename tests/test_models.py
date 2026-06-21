"""Tests for all new and updated model dataclasses."""

from pystructurizr.models import (
    Animation,
    AutomaticLayout,
    Border,
    ColorScheme,
    Component,
    Configuration,
    Container,
    ContainerInstance,
    CustomElement,
    DeploymentNode,
    ElementStyle,
    Enterprise,
    FilterMode,
    HttpHealthCheck,
    IconPosition,
    InfrastructureNode,
    InteractionStyle,
    LineStyle,
    Location,
    PaperSize,
    Perspective,
    Person,
    RankDirection,
    Relationship,
    RelationshipStyle,
    RelationshipView,
    Routing,
    Shape,
    SoftwareSystem,
    SoftwareSystemInstance,
    Styles,
    Terminology,
    Vertex,
    View,
    ViewElement,
    ViewSortOrder,
    ViewType,
    Workspace,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


def test_location_enum_values() -> None:
    assert Location.INTERNAL == "Internal"
    assert Location.EXTERNAL == "External"
    assert Location.UNSPECIFIED == "Unspecified"


def test_interaction_style_enum() -> None:
    assert InteractionStyle.SYNCHRONOUS == "Synchronous"
    assert InteractionStyle.ASYNCHRONOUS == "Asynchronous"


def test_rank_direction_enum() -> None:
    assert RankDirection.TOP_BOTTOM == "TopBottom"
    assert RankDirection.LEFT_RIGHT == "LeftRight"


def test_shape_enum_has_all_values() -> None:
    assert Shape.BOX == "Box"
    assert Shape.PERSON == "Person"
    assert Shape.COMPONENT == "Component"


def test_view_type_has_new_values() -> None:
    assert ViewType.SYSTEM_LANDSCAPE == "systemLandscape"
    assert ViewType.CUSTOM == "custom"
    assert ViewType.IMAGE == "image"
    assert ViewType.FILTERED == "filtered"


def test_paper_size_enum() -> None:
    assert PaperSize.A4_PORTRAIT == "A4_Portrait"
    assert PaperSize.SLIDE_16_9 == "Slide_16_9"


# ---------------------------------------------------------------------------
# Supporting value object tests
# ---------------------------------------------------------------------------


def test_perspective_defaults() -> None:
    p = Perspective(name="Security")
    assert p.description == ""
    assert p.value == ""
    assert p.url == ""
    assert p.title == ""


def test_perspective_with_title() -> None:
    p = Perspective(name="Security", title="Security View")
    assert p.title == "Security View"


def test_enterprise_name() -> None:
    e = Enterprise(name="Acme Corp")
    assert e.name == "Acme Corp"


def test_http_health_check_defaults() -> None:
    h = HttpHealthCheck(name="ping", url="https://example.com/health")
    assert h.interval == 60
    assert h.timeout == 0
    assert h.headers == {}


def test_automatic_layout_defaults() -> None:
    al = AutomaticLayout()
    assert al.rank_direction == RankDirection.TOP_BOTTOM
    assert al.rank_separation == 100
    assert al.node_separation == 100
    assert al.vertices is False


def test_automatic_layout_custom() -> None:
    al = AutomaticLayout(rank_direction=RankDirection.LEFT_RIGHT, rank_separation=200)
    assert al.rank_direction == RankDirection.LEFT_RIGHT
    assert al.rank_separation == 200


def test_vertex() -> None:
    v = Vertex(x=10, y=20)
    assert v.x == 10
    assert v.y == 20


def test_animation() -> None:
    a = Animation(order=1, element_ids=["a", "b"], relationship_ids=["r1"])
    assert a.order == 1
    assert len(a.element_ids) == 2


# ---------------------------------------------------------------------------
# Relationship tests
# ---------------------------------------------------------------------------


def test_relationship_new_fields() -> None:
    r = Relationship(source_id="a", destination_id="b")
    assert r.id == ""
    assert r.interaction_style == InteractionStyle.SYNCHRONOUS
    assert r.linked_relationship_id == ""
    assert r.url == ""
    assert r.properties == {}
    assert r.perspectives == []


def test_relationship_async() -> None:
    r = Relationship(
        source_id="a",
        destination_id="b",
        interaction_style=InteractionStyle.ASYNCHRONOUS,
    )
    assert r.interaction_style == InteractionStyle.ASYNCHRONOUS


# ---------------------------------------------------------------------------
# Static element field tests
# ---------------------------------------------------------------------------


def test_person_new_fields() -> None:
    p = Person(id="u1", name="Alice")
    assert p.location == Location.UNSPECIFIED
    assert p.url == ""
    assert p.properties == {}
    assert p.perspectives == []
    assert p.group == ""


def test_person_external_location() -> None:
    p = Person(id="u1", name="Alice", location=Location.EXTERNAL)
    assert p.location == Location.EXTERNAL


def test_software_system_new_fields() -> None:
    s = SoftwareSystem(id="s1", name="My System")
    assert s.location == Location.UNSPECIFIED
    assert s.url == ""
    assert s.properties == {}
    assert s.group == ""


def test_container_new_fields() -> None:
    c = Container(id="c1", name="API")
    assert c.url == ""
    assert c.properties == {}
    assert c.perspectives == []
    assert c.group == ""


def test_component_new_fields() -> None:
    comp = Component(id="comp1", name="Controller")
    assert comp.url == ""
    assert comp.properties == {}
    assert comp.group == ""


def test_custom_element() -> None:
    ce = CustomElement(id="ce1", name="My Box", metadata="box")
    assert ce.metadata == "box"
    assert ce.tags == []
    assert ce.group == ""


# ---------------------------------------------------------------------------
# Deployment element tests
# ---------------------------------------------------------------------------


def test_infrastructure_node_defaults() -> None:
    n = InfrastructureNode(id="lb1", name="Load Balancer")
    assert n.technology == ""
    assert n.properties == {}
    assert n.group == ""


def test_software_system_instance_defaults() -> None:
    i = SoftwareSystemInstance(id="ssi1", software_system_id="ss1")
    assert i.instance_id == 1
    assert i.environment == ""
    assert i.health_checks == []
    assert i.deployment_groups == []


def test_container_instance_defaults() -> None:
    i = ContainerInstance(id="ci1", container_id="c1")
    assert i.instance_id == 1
    assert i.health_checks == []


def test_deployment_node_defaults() -> None:
    dn = DeploymentNode(id="dn1", name="AWS")
    assert dn.technology == ""
    assert dn.instances == 1
    assert dn.environment == ""
    assert dn.children == []
    assert dn.infrastructure_nodes == []
    assert dn.software_system_instances == []
    assert dn.container_instances == []


def test_deployment_node_nesting() -> None:
    child = DeploymentNode(id="child", name="EC2")
    parent = DeploymentNode(id="parent", name="AWS", children=[child])
    assert len(parent.children) == 1
    assert parent.children[0].name == "EC2"


def test_parent_id_defaults_empty() -> None:
    assert Container(id="c1", name="API").parent_id == ""
    assert Component(id="cmp1", name="X").parent_id == ""
    assert DeploymentNode(id="dn1", name="AWS").parent_id == ""
    assert InfrastructureNode(id="i1", name="LB").parent_id == ""


def test_parent_id_can_be_set() -> None:
    c = Container(id="c1", name="API", parent_id="sys1")
    assert c.parent_id == "sys1"
    cmp = Component(id="cmp1", name="X", parent_id="c1")
    assert cmp.parent_id == "c1"
    dn = DeploymentNode(id="dn2", name="EC2", parent_id="dn1")
    assert dn.parent_id == "dn1"
    infra = InfrastructureNode(id="i1", name="LB", parent_id="dn1")
    assert infra.parent_id == "dn1"


# ---------------------------------------------------------------------------
# View model tests
# ---------------------------------------------------------------------------


def test_view_new_fields() -> None:
    v = View(type=ViewType.SYSTEM_CONTEXT, key="ctx")
    assert v.auto_layout is None
    assert v.order == 0
    assert v.properties == {}
    assert v.paper_size is None
    assert v.relationship_views == []
    assert v.animations == []


def test_view_with_auto_layout() -> None:
    v = View(
        type=ViewType.SYSTEM_CONTEXT,
        key="ctx",
        auto_layout=AutomaticLayout(rank_direction=RankDirection.LEFT_RIGHT),
    )
    assert v.auto_layout is not None
    assert v.auto_layout.rank_direction == RankDirection.LEFT_RIGHT


def test_relationship_view_defaults() -> None:
    rv = RelationshipView(id="r1")
    assert rv.description == ""
    assert rv.order == ""
    assert rv.response is None
    assert rv.vertices == []
    assert rv.routing is None


# ---------------------------------------------------------------------------
# Styling model tests
# ---------------------------------------------------------------------------


def test_element_style_defaults() -> None:
    es = ElementStyle(tag="Person")
    assert es.width is None
    assert es.background == ""
    assert es.shape is None
    assert es.opacity is None


def test_relationship_style_defaults() -> None:
    rs = RelationshipStyle(tag="Relationship")
    assert rs.thickness is None
    assert rs.dashed is None
    assert rs.routing is None


def test_styles_empty() -> None:
    s = Styles()
    assert s.element_styles == []
    assert s.relationship_styles == []


def test_terminology_defaults() -> None:
    t = Terminology()
    assert t.enterprise == "Enterprise"
    assert t.person == "Person"
    assert t.software_system == "Software System"
    assert t.container == "Container"
    assert t.component == "Component"
    assert t.code == "Code"
    assert t.deployment_node == "Deployment Node"
    assert t.infrastructure_node == "Infrastructure Node"
    assert t.relationship == "Relationship"


def test_configuration_defaults() -> None:
    c = Configuration()
    assert c.themes == []
    assert c.default_view == ""
    assert c.view_sort_order is None


# ---------------------------------------------------------------------------
# Workspace tests
# ---------------------------------------------------------------------------


def test_workspace_new_fields() -> None:
    ws = Workspace(name="Test")
    assert ws.deployment_nodes == []
    assert ws.deployment_environments == []
    assert ws.enterprise is None
    assert isinstance(ws.configuration, Configuration)


def test_workspace_metadata_defaults() -> None:
    ws = Workspace(name="Test")
    assert ws.id == ""
    assert ws.version == 1
    assert ws.revision == 1
    assert ws.last_modified_date == ""
    assert ws.last_modified_by == ""
    assert ws.created_date == ""
    assert ws.created_by == ""


def test_workspace_metadata_set() -> None:
    ws = Workspace(
        name="Test",
        id="42",
        version=7,
        revision=3,
        last_modified_date="2026-06-21T10:00:00Z",
        last_modified_by="alice",
        created_date="2026-01-01T00:00:00Z",
        created_by="bob",
    )
    assert ws.id == "42"
    assert ws.version == 7
    assert ws.last_modified_by == "alice"
    assert ws.created_by == "bob"


def test_view_element_customization_fields() -> None:
    ve = ViewElement(id="e1", title="Custom", description="d", width=120, height=80)
    assert ve.title == "Custom"
    assert ve.description == "d"
    assert ve.width == 120
    assert ve.height == 80


def test_relationship_view_link_fields() -> None:
    rv = RelationshipView(id="r1", title="Calls", link=True, link_element=2)
    assert rv.title == "Calls"
    assert rv.link is True
    assert rv.link_element == 2


def test_view_control_flag_defaults() -> None:
    v = View(type=ViewType.SYSTEM_CONTEXT, key="k")
    assert v.owner == ""
    assert v.disable_automatic_layout is False
    assert v.hide_element_metadata is False
    assert v.hide_relationship_metadata is False


def test_view_control_flags_set() -> None:
    v = View(
        type=ViewType.SYSTEM_CONTEXT,
        key="k",
        owner="alice",
        disable_automatic_layout=True,
        hide_element_metadata=True,
        hide_relationship_metadata=True,
    )
    assert v.owner == "alice"
    assert v.disable_automatic_layout is True
    assert v.hide_element_metadata is True
    assert v.hide_relationship_metadata is True


def test_deployment_and_infra_icon_default_empty() -> None:
    assert DeploymentNode(id="dn1", name="AWS").icon == ""
    assert InfrastructureNode(id="lb1", name="LB").icon == ""


def test_deployment_and_infra_icon_set() -> None:
    dn = DeploymentNode(id="dn1", name="AWS", icon="aws-logo.png")
    infra = InfrastructureNode(id="lb1", name="LB", icon="nginx.svg")
    assert dn.icon == "aws-logo.png"
    assert infra.icon == "nginx.svg"


def test_workspace_find_element_in_deployment_node() -> None:
    infra = InfrastructureNode(id="lb1", name="LB")
    dn = DeploymentNode(id="dn1", name="AWS", infrastructure_nodes=[infra])
    ws = Workspace(name="W", deployment_nodes=[dn])
    assert ws.find_element("dn1") is dn
    assert ws.find_element("lb1") is infra
    assert ws.find_element("missing") is None


def test_workspace_find_element_nested_deployment() -> None:
    child = DeploymentNode(id="child", name="EC2")
    parent = DeploymentNode(id="parent", name="AWS", children=[child])
    ws = Workspace(name="W", deployment_nodes=[parent])
    assert ws.find_element("child") is child


def test_workspace_enterprise() -> None:
    ws = Workspace(name="W", enterprise=Enterprise(name="Acme"))
    assert ws.enterprise is not None
    assert ws.enterprise.name == "Acme"
