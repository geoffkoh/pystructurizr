import json
from pathlib import Path
from pystructurizr.models import Location
from pystructurizr.parser.json_parser import parse_json, parse_json_file

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_json_fixture():
    ws = parse_json_file(FIXTURES / "example.json")
    assert ws.name == "Internet Banking"
    assert len(ws.people) == 1
    assert ws.people[0].name == "Personal Banking Customer"
    assert len(ws.software_systems) == 2


def test_parse_json_relationships():
    ws = parse_json_file(FIXTURES / "example.json")
    assert len(ws.relationships) > 0
    rels_from_customer = [r for r in ws.relationships if r.source_id == "1"]
    assert len(rels_from_customer) == 2


def test_parse_json_containers():
    ws = parse_json_file(FIXTURES / "example.json")
    banking = next(s for s in ws.software_systems if s.name == "Internet Banking System")
    assert len(banking.containers) == 3


def test_parse_json_views():
    ws = parse_json_file(FIXTURES / "example.json")
    assert len(ws.views) == 2
    keys = {v.key for v in ws.views}
    assert "SystemContext" in keys
    assert "Containers" in keys


def test_external_system_flag():
    ws = parse_json_file(FIXTURES / "example.json")
    email = next(s for s in ws.software_systems if s.name == "E-mail System")
    assert email.location == Location.EXTERNAL


def test_parse_workspace_metadata_from_json():
    raw = json.dumps({
        "workspace": {
            "id": "999",
            "name": "Banking",
            "version": 5,
            "revision": 12,
            "lastModifiedDate": "2026-06-20T11:00:00Z",
            "lastModifiedUser": "alice",
            "createdDate": "2026-01-15T09:00:00Z",
            "createdUser": "bob",
            "model": {},
        }
    })
    ws = parse_json(raw)
    assert ws.id == "999"
    assert ws.version == 5
    assert ws.revision == 12
    assert ws.last_modified_date == "2026-06-20T11:00:00Z"
    assert ws.last_modified_by == "alice"
    assert ws.created_date == "2026-01-15T09:00:00Z"
    assert ws.created_by == "bob"


def test_parse_view_control_flags_from_json():
    raw = json.dumps({
        "workspace": {
            "name": "W",
            "model": {},
            "views": {
                "systemContextViews": [{
                    "key": "ctx",
                    "owner": "alice",
                    "disableAutomaticLayout": True,
                    "hideElementMetadata": True,
                    "hideRelationshipMetadata": True,
                }],
            },
        }
    })
    ws = parse_json(raw)
    v = ws.views[0]
    assert v.owner == "alice"
    assert v.disable_automatic_layout is True
    assert v.hide_element_metadata is True
    assert v.hide_relationship_metadata is True


def test_parse_relationship_view_link_fields_from_json():
    raw = json.dumps({
        "workspace": {
            "name": "W",
            "model": {},
            "views": {
                "systemContextViews": [{
                    "key": "ctx",
                    "relationships": [
                        {"id": "r1", "title": "Calls", "link": True, "linkElement": 7}
                    ],
                }],
            },
        }
    })
    ws = parse_json(raw)
    rv = ws.views[0].relationship_views[0]
    assert rv.title == "Calls"
    assert rv.link is True
    assert rv.link_element == 7


def test_parse_deployment_and_infra_icon_from_json():
    raw = json.dumps({
        "workspace": {
            "name": "W",
            "model": {
                "deploymentNodes": [{
                    "id": "1", "name": "AWS", "icon": "aws.png",
                    "infrastructureNodes": [{"id": "2", "name": "LB", "icon": "nginx.svg"}],
                }],
            },
        }
    })
    ws = parse_json(raw)
    aws = ws.deployment_nodes[0]
    assert aws.icon == "aws.png"
    assert aws.infrastructure_nodes[0].icon == "nginx.svg"
