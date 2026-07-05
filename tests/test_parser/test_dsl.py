from pathlib import Path
import pytest
from pystructurizr.parser.dsl import ParseError, parse_dsl, parse_dsl_file

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


def test_include_multiple_identifiers_on_one_line():
    dsl = """
    workspace {
        model {
            a = person "A"
            b = person "B"
            s = softwareSystem "S"
            a -> s "Uses"
        }
        views {
            systemContext s "v" {
                include a b s
                exclude b
                autoLayout
            }
        }
    }
    """
    ws = parse_dsl(dsl)
    view = ws.views[0]
    a, b, s = ws.people[0].id, ws.people[1].id, ws.software_systems[0].id
    assert view.included_ids == [a, b, s]
    assert view.excluded_ids == [b]
    # autoLayout on the next line must not be swallowed as an included id.
    assert view.auto_layout is not None


def test_include_splits_workspace_across_files():
    ws = parse_dsl_file(FIXTURES / "split_workspace" / "workspace.dsl")
    assert ws.name == "Split Workspace"
    assert len(ws.people) == 1
    assert len(ws.software_systems) == 1
    assert ws.software_systems[0].containers[0].name == "API"
    # Relationship declared in a nested include, across fragment files.
    assert len(ws.relationships) == 1
    assert ws.relationships[0].description == "Calls"
    assert len(ws.views) == 1


def test_include_missing_file_raises(tmp_path: Path):
    main = tmp_path / "workspace.dsl"
    main.write_text(
        'workspace "W" { model {\n!include missing.dsl\n} }', encoding="utf-8"
    )
    with pytest.raises(ParseError, match="not found"):
        parse_dsl_file(main)


def test_include_cycle_raises(tmp_path: Path):
    a = tmp_path / "a.dsl"
    b = tmp_path / "b.dsl"
    a.write_text('workspace "W" { model {\n!include b.dsl\n} }', encoding="utf-8")
    b.write_text("!include a.dsl\n", encoding="utf-8")
    with pytest.raises(ParseError, match="Circular"):
        parse_dsl_file(a)


def test_include_without_file_context_raises():
    with pytest.raises(ParseError, match="file context"):
        parse_dsl('workspace "W" { model {\n!include other.dsl\n} }')


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
