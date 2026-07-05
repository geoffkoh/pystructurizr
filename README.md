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

## React Web App

A React (Vite + TypeScript) single-page app, served by a FastAPI backend
and launched from the CLI, for loading DSL/JSON files from disk and
exploring each view as an interactive [React Flow](https://reactflow.dev/)
graph (draggable nodes, pan/zoom, minimap).

```bash
uv run pystructurizr webapp samples/          # browse a directory
uv run pystructurizr webapp file.dsl          # preload a single file
# → opens http://127.0.0.1:8090 (use --no-browser to skip, --port to change)
```

Pass a directory to browse and load any `.dsl`/`.json` file from the
in-app file picker, or a single file to preload it. The element tree and
per-view graph come from the parser and `webapp/g6_view`; only
`systemContext`/`container`/`component` views render a graph today
(others are flagged "not renderable yet").

The built SPA ships inside the package (`pystructurizr/webapp/static/`),
so end users need no Node toolchain. To rebuild the frontend after
changes (requires Node 18+):

```bash
cd frontend
npm install
npm run build          # outputs to ../src/pystructurizr/webapp/static/
# dev loop: `npm run dev` (Vite :5173, proxies /api → :8090) alongside
#           `uv run pystructurizr webapp samples/ --no-browser`
```

> **Security**: the web app has no authentication and is intended for
> local use on `127.0.0.1`.

### Tests

```bash
uv run pytest                      # full suite
uv run pytest tests/test_webapp    # web app tests only
```
