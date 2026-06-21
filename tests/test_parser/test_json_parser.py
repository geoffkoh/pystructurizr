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
