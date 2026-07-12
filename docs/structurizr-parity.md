# Feature parity: pystructurizr webapp vs. Java Structurizr UI

An assessment of the original Java Structurizr web application
(`structurizr-application` — the codebase behind Structurizr Lite /
on-premises, JSP + JointJS) against the pystructurizr React webapp.
Originally written in July 2026 from a source-level review of
`structurizr-application` (JSP views, `structurizr-diagram.js` ~8k LOC,
`structurizr-ui.js`); updated after the PP-42…PP-49 roadmap landed, which
implemented every item in the original recommended roadmap.

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
| System landscape views | ✅ | ✅ | With enterprise boundary around internal elements |
| System context / container / component views | ✅ | ✅ | Correct C4 semantics incl. implied-relationship lifting |
| Dynamic views + animation steps | ✅ | ✅ | Ordered numbered steps; All/prev/next/play controls with step highlighting and dimming |
| Deployment views | ✅ | ✅ | Nested deployment nodes, container/system instances, derived instance edges, environment + scope filtering |
| Boundary nesting | ✅ | ✅ | Nested group nodes, any depth |
| Expand element in place | ❌ (navigation only) | ✅ | Multiple containers expandable inside a container view — pystructurizr goes beyond the Java UI here |
| Tag-based styles (colours, text colour) | ✅ | ✅ | DSL `styles` block; implicit Element/kind tags, declaration-order overrides |
| Shapes | ✅ (full set) | ✅ | Person/Robot, Cylinder/Bucket, Box, Circle/Ellipse, Pipe, Hexagon, Folder, WebBrowser/Window, MobileDevice portrait/landscape; remaining exotics fall back to rounded box |
| Themes (remote theme URLs) | ✅ | ✅ | `theme "https://..."` fetched, cached and merged (workspace styles win); official AWS/Azure/GCP themes attach service logo icons |
| Element icons | ✅ | ✅ | `icon` style property and theme icons render in the node |
| Element metadata (`[Container: Tech]` + description) | ✅ | ✅ | |
| Auto-layout | ✅ (dagre, per-view direction) | ✅ | Recursive compound dagre; honours `autoLayout lr/tb/bt/rl` |
| Drag nodes / persist layout | ✅ (full editor) | ✅ | Drag autosaves to a `<source>.layout.json` sidecar, restored on load and live reload; Reset returns to auto-layout. Multi-level-nested views re-run auto-layout on restore |
| Edge routing | ✅ (orthogonal/curved, manual vertices) | ✅ | Bezier / straight / step / smooth-step, centre-anchored floating anchors; no manual vertices |
| PNG/SVG export | ✅ | ✅ | Toolbar buttons; diagram-bounds crop, 2× PNG |
| Filtered / custom / image views | ✅ | ❌ | Long tail |
| Perspectives / animation of static views / health checks | ✅ | ❌ | Long tail |

## Navigation & exploration

| Feature | Java UI | pystructurizr |
| --- | --- | --- |
| Double-click drill-in (landscape → context → container → component) | ✅ | ✅ |
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
| Live reload on DSL edits | ✅ | ✅ mtime heartbeat over source + `!include` fragments + docs; parse errors keep the last good workspace |
| In-browser DSL editor | ✅ | ❌ (edit on disk; live reload covers the loop) |
| Documentation / ADR rendering | ✅ | ✅ `!docs`/`!adrs` directives, TOC reader, ADR status badges |
| Workspace JSON import | ✅ | ✅ |
| Workspace JSON export (round-trip) | ✅ | ✅ CLI `export` + `generators/json_export` |
| Layout persistence | ✅ (in workspace) | ✅ (sidecar JSON next to the source) |
| Multi-workspace, users, locking, branches | ✅ | ❌ (single local user by design) |
| Mermaid export | ❌ (PlantUML et al. via structurizr-export) | ✅ CLI |

## Roadmap status

The original recommended roadmap is fully implemented (Jira PP-42…PP-49,
PRs #20–#27): tag-based styles, autoLayout direction, PNG/SVG export,
live reload, system landscape views, dynamic views with animation,
documentation/ADR pages, and layout persistence.

### Remaining gaps, should they ever be worth closing

1. **Full-model explorer and search** — a d3-style model graph plus
   element search outside curated views.
2. **In-browser DSL editor** — live reload already gives a tight loop
   with an external editor, so this is convenience rather than capability.
3. **Filtered / custom / image views, perspectives** — long-tail
   Structurizr features with niche usage.
4. **Manual edge vertices** — point-to-point routing control on top of
   the floating edges.
