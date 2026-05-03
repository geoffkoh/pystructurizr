from pathlib import Path
import pytest
from pystructurizr.parser.dsl import parse_dsl, parse_dsl_file

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_parse_minimal():
    dsl = """
    workspace "Test" "desc" {
        model {
            u = person "User"
            s = softwareSystem "System"
            u -> s "Uses"
        }
        views {
            systemContext s "ctx" {
                include *
            }
        }
    }
    """
    ws = parse_dsl(dsl)
    assert ws.name == "Test"
    assert len(ws.people) == 1
    assert ws.people[0].name == "User"
    assert len(ws.software_systems) == 1
    assert ws.software_systems[0].name == "System"
    assert len(ws.relationships) == 1
    assert ws.relationships[0].description == "Uses"


def test_parse_containers():
    dsl = """
    workspace "W" {
        model {
            s = softwareSystem "MySystem" {
                c1 = container "Web App" "UI" "React"
                c2 = container "API" "Backend" "Python"
                c1 -> c2 "Calls"
            }
        }
        views {
            container s "ContView" {
                include *
            }
        }
    }
    """
    ws = parse_dsl(dsl)
    system = ws.software_systems[0]
    assert len(system.containers) == 2
    assert system.containers[0].technology == "React"
    assert len(ws.relationships) == 1


def test_parse_example_fixture():
    ws = parse_dsl_file(FIXTURES / "example.dsl")
    assert ws.name == "Internet Banking"
    assert len(ws.people) == 1
    assert len(ws.software_systems) == 3
    bank = next(s for s in ws.software_systems if "Banking System" in s.name)
    assert len(bank.containers) == 4
    assert len(ws.views) == 2


def test_relationship_technology():
    dsl = """
    workspace {
        model {
            a = person "A"
            b = softwareSystem "B"
            a -> b "Uses" "HTTPS"
        }
        views { systemContext b "v" { include * } }
    }
    """
    ws = parse_dsl(dsl)
    assert ws.relationships[0].technology == "HTTPS"
