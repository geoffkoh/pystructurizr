# pystructurizr

Python implementation of [Structurizr](https://structurizr.com/) for architecture modeling and C4 diagram generation.

## Quick Start

```python
from pystructurizr.models import Workspace, Person, SoftwareSystem, Container, Relationship, View, ViewType

# Create workspace
ws = Workspace(
    name="My Architecture",
    description="System architecture model"
)

# Define people and systems
user = Person(id="user", name="User")
system = SoftwareSystem(id="sys", name="System")
ws.people.append(user)
ws.software_systems.append(system)

# Add relationship
rel = Relationship(
    source_id="user",
    destination_id="sys",
    description="Uses"
)
ws.relationships.append(rel)

# Create view
view = View(type=ViewType.SYSTEM_CONTEXT, key="context")
ws.views.append(view)
```

## Documentation

- **[Data Models Reference](./docs/data-models.md)** - Complete guide to all Structurizr models and their fields
- **[Getting Started](./docs/README.md)** - Workflow and common patterns

## Features

- ✅ Full Structurizr metamodel support (C4 architecture model)
- ✅ DSL and JSON parsing
- ✅ Mermaid C4 diagram generation
- ✅ Comprehensive type hints
- ✅ Custom properties and perspectives on all elements
- ✅ Deployment infrastructure modeling
- ✅ Style and configuration management

## Parsing

Parse Structurizr DSL or JSON files:

```python
from pystructurizr.parser.dsl import parse_dsl_file
from pystructurizr.parser.json_parser import parse_json_file

# Parse DSL
ws = parse_dsl_file("architecture.dsl")

# Parse JSON
ws = parse_json_file("workspace.json")
```

## Diagram Generation

Generate Mermaid C4 diagrams:

```python
from pystructurizr.generators.mermaid import MermaidGenerator

gen = MermaidGenerator(ws)
diagrams = gen.generate_all()

for view_name, mermaid_code in diagrams.items():
    print(f"{view_name}:\n{mermaid_code}\n")
```

## Interactive Viewer

A NiceGUI-based viewer is included for exploring a workspace and laying
out views interactively.

```bash
uv run python -m pystructurizr.viewer.app
# → http://localhost:8765
```

Features:

- **Folder input** — point at a directory containing `workspace.dsl`.
- **Hierarchical tree** — People, Software Systems → Containers →
  Components, Deployment Nodes (recursive) → Infra/Instances, plus a
  Views branch keyed by view key.
- **Mermaid canvas** — click any view; the existing
  `MermaidGenerator` renders it.
- **Cytoscape canvas** — toggle to a Cytoscape.js renderer for the same
  view; nodes are draggable, pan/zoom built in.
- **Save** — persists per-view node positions
  (`View.element_views[i].x/y`) to `workspace.json` next to the loaded
  DSL. The DSL itself is never modified.

The viewer loads Cytoscape from CDN (`unpkg.com/cytoscape@3`); no build
step required.

### Tests

```bash
uv run pytest                      # full suite
uv run pytest tests/test_viewer    # viewer-only smoke tests
```
