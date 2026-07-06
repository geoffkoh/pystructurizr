# Feature parity: pystructurizr webapp vs. Java Structurizr UI

An assessment of the original Java Structurizr web application
(`structurizr-application` — the codebase behind Structurizr Lite /
on-premises, JSP + JointJS) against the pystructurizr React webapp, to steer
pystructurizr toward a bona fide solution-architecture visualization
toolset. Based on a source-level review of `structurizr-application`
(JSP views, `structurizr-diagram.js` ~8k LOC, `structurizr-ui.js`) in
July 2026.

## Where the Java UI's functionality lives

| Java surface | What it does |
| --- | --- |
| `diagrams.jsp` + `structurizr-diagram.js` | Interactive diagram editor (JointJS): rendering, layout, styling, editing |
| `documentation.jsp`, `decisions.jsp` | Markdown/AsciiDoc docs and ADRs with embedded diagrams |
| `explore.jsp`, `graph.jsp`, `tree.jsp`, `model.jsp` | Model exploration outside curated views |
| `dsl-editor.jsp` | In-browser DSL editing with live re-render |
| `theme-browser.jsp`, themes/styles engine | Tag-based element/relationship styling, shared themes |
| workspace API + locking/branches/users | Multi-user workspace management |

## Diagram rendering

| Feature | Java UI | pystructurizr | Notes |
| --- | --- | --- | --- |
| System context / container / component views | ✅ | ✅ | Correct C4 semantics incl. implied-relationship lifting |
| Boundary nesting | ✅ | ✅ | Nested group nodes, any depth |
| Deployment views | ✅ | ✅ | Nested deployment nodes, container/system instances, derived instance edges, environment + scope filtering |
| Expand element in place | ❌ (navigation only) | ✅ | Multiple containers expandable inside a container view — pystructurizr goes beyond the Java UI here |
| Person shape | ✅ | ✅ | C4 silhouette |
| Element metadata (`[Container: Tech]` + description) | ✅ | ✅ | |
| Auto-layout | ✅ (dagre, per-view direction) | ✅ (dagre, recursive compound) | Java honours `autoLayout lr/tb` direction — pystructurizr always TB (roadmap) |
| Drag nodes / persist layout | ✅ (full editor) | ◐ | Dragging works; persistence API exists but is not wired to the UI |
| Edge routing | ✅ (orthogonal/curved, manual vertices) | ✅ | Bezier / straight / step / smooth-step, centre-anchored floating anchors |
| Dynamic views + animation steps | ✅ | ❌ | Roadmap |
| System landscape / filtered / custom / image views | ✅ | ❌ | Landscape is close to context-view semantics (roadmap) |
| Tag-based styles & themes (shapes, colours, icons) | ✅ | ❌ | pystructurizr uses a fixed kind palette; `styles`/`theme` blocks are parsed but skipped. Highest-value gap |
| Shapes (cylinder, pipe, robot, browser, …) | ✅ | ❌ | Depends on styles support |
| PNG/SVG export | ✅ | ❌ | React Flow supports viewport-to-image (roadmap) |
| Perspectives / filters / health checks | ✅ | ❌ | Long tail |

## Navigation & exploration

| Feature | Java UI | pystructurizr |
| --- | --- | --- |
| Double-click drill-in (context → container → component) | ✅ | ✅ |
| Drill-out | ◐ (back button) | ✅ breadcrumb + boundary double-click |
| View list / quick navigation | ✅ | ✅ sidebar |
| Element tree | ✅ (`tree.jsp`) | ✅ sidebar |
| Full-model graph exploration | ✅ (`explore.jsp`, d3) | ❌ |
| Search | ✅ | ❌ |
| Keyboard shortcuts | ✅ | ❌ |

## Authoring & workspace management

| Feature | Java UI | pystructurizr |
| --- | --- | --- |
| DSL parsing incl. `!include` | ✅ | ✅ |
| `deploymentEnvironment`, instances | ✅ | ✅ |
| In-browser DSL editor with live refresh | ✅ | ❌ (edit on disk, reload file) |
| Documentation / ADR rendering | ✅ | ❌ (model exists in `pystructurizr.models.documentation`) |
| Workspace JSON import | ✅ | ✅ |
| Workspace JSON export / save | ✅ | ◐ (layout save endpoint writes JSON) |
| Multi-workspace, users, locking, branches | ✅ | ❌ (single local user by design) |
| Mermaid export | ❌ (PlantUML et al. via structurizr-export) | ✅ CLI |

## Recommended roadmap (highest value first)

1. **Tag-based element styles** — parse the DSL `styles` block (colours,
   shapes) and apply it in `ElementNode`; unlocks cylinders for databases,
   custom palettes, and theme fidelity. Most visible parity gap.
2. **Auto-layout direction** — honour `autoLayout lr|tb|bt|rl` from the DSL
   in the dagre layout.
3. **PNG/SVG export** of the current view.
4. **File watching / live reload** so editing the DSL on disk refreshes the
   browser (poor man's DSL editor; a full in-browser editor can come later).
5. **System landscape views** (reuses context-view machinery).
6. **Dynamic views** with ordered relationship animation.
7. **Documentation/ADR pages** — the dataclasses already model docs;
   render markdown alongside diagrams.
8. **Layout persistence UI** — wire the existing save-layout endpoint to
   node drag events.
