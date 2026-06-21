# Task: Build a NiceGUI viewer for pystructurizr workspaces

You are working on a Python project at `/Users/geoffkoh/Development/claude/pystructurizr`.

## Assumptions (change these here, not deeper in the prompt)
- Web framework: NiceGUI (`uv add nicegui`)
- Diagram library: Cytoscape.js (loaded from CDN). NOT react-flow — react-flow requires a React build pipeline that NiceGUI doesn't ship; Cytoscape gives equivalent drag/zoom/select in a single `<script>` tag.
- First-cut renderer: `ui.mermaid()` using the existing `pystructurizr.generators.mermaid` (ship a working viewer fast, then layer Cytoscape).
- App lives under a new top-level package: `src/pystructurizr/viewer/`.

## Conventions you MUST follow
- `uv add nicegui` before importing it; do not edit pyproject.toml by hand.
- Branch: `feature/nicegui-viewer` (already created from main; do NOT switch branches).
- Semantic commits (`feat:`, `fix:`, `chore:`); one commit per milestone below. Push after each commit.
- mypy --strict must stay clean on viewer code.
- Use python-pro subagent for non-trivial Python module skeletons (NiceGUI patterns, async handlers, JS bridge). Use Explore for "where is X" lookups inside pystructurizr.

## Resumability
At the start of every iteration, run `git status`, `git log --oneline -10`, and `ls src/pystructurizr/viewer/ 2>/dev/null` to figure out which milestone you're on. Pick up from the next un-done one. Do NOT redo work that's already committed.

## Milestones — commit + push after each

### M1: Skeleton + folder input
- `src/pystructurizr/viewer/__init__.py` exposes `main`.
- `src/pystructurizr/viewer/app.py` exposes `main()` that calls `ui.run(...)`.
- Layout: `ui.header` with title, `ui.splitter` for side panel + main area.
- Side: empty `ui.tree(label='Workspace')` and a folder-path `ui.input` + Load button.
- Main: placeholder `ui.label('Load a workspace to begin')`.
- `uv run python -m pystructurizr.viewer.app` boots without errors (verify briefly with a 5-second timeout, then kill).
- Commit message: `feat(viewer): skeleton layout with folder input (M1)`

### M2: DSL loading
- Load button reads `<folder>/workspace.dsl`, calls `parse_dsl_file`, stashes the Workspace in `app.storage.user` (or a module-level singleton; pick one and stick with it).
- Error path: show a `ui.notify` if file missing or parse fails.
- Don't redraw the tree yet — just confirm load works via a notify.
- Commit message: `feat(viewer): load workspace.dsl from folder input (M2)`

### M3: Hierarchical tree
- Populate `ui.tree` with nodes for: People, Software Systems → Containers → Components, Deployment Nodes → Infra/Instances, Custom Elements.
- Each leaf carries the element id in its `value` so we can dispatch on click.
- Add a "Views" branch listing every `ws.views.get_all_views()` entry by key.
- Commit message: `feat(viewer): hierarchical element tree from loaded workspace (M3)`

### M4: View selector + Mermaid canvas
- Clicking a view in the tree calls `MermaidGenerator(ws).generate_all()[key]` and renders via `ui.mermaid(...)` in the main pane.
- Cache the rendered string per key.
- App is now usable end-to-end with Mermaid output.
- Commit message: `feat(viewer): render selected view via Mermaid (M4)`
- After pushing, **report back to the user that v0.1 is shippable** and ask whether to continue with M5–M7 or pause. Use this as a natural checkpoint.

### M5: Cytoscape canvas (parallel to Mermaid; user can toggle)
- Inject Cytoscape via `ui.add_head_html('<script src="https://unpkg.com/cytoscape@3/dist/cytoscape.min.js"></script>')`.
- Build a small `cytoscape_view.py` that translates a selected View → cytoscape elements (nodes + edges with positions if `ViewElement.x/y` set).
- Render in `ui.html('<div id="cy"></div>')` with a `ui.run_javascript(...)` call that wires `cytoscape({ container: ..., elements: ..., layout: { name: 'cose' } })`.
- Add a toggle (`ui.toggle(['Mermaid', 'Cytoscape'])`) above the canvas.
- Commit message: `feat(viewer): Cytoscape.js canvas with mermaid/cytoscape toggle (M5)`

### M6: Drag-and-drop persistence
- Listen to Cytoscape's `dragfree` event; on drop, post node positions back to NiceGUI via `ui.run_javascript`'s response channel or an emit.
- Update the corresponding `ViewElement.x/y` on the Workspace.
- "Save" button writes the updated workspace back to a JSON file (`workspace.json` next to the DSL); do NOT modify the DSL file in this milestone.
- Commit message: `feat(viewer): persist drag-and-drop layout to JSON (M6)`

### M7: Polish + tests
- Headless smoke test: `tests/test_viewer/test_app.py` boots the app, sends a fake load, asserts tree has expected nodes (use `nicegui.testing.User`).
- `uv run pytest` stays green.
- README section: how to run, what's supported.
- Commit message: `feat(viewer): smoke tests + README docs (M7)`

## Stop-and-ask conditions
If any of these happen, commit what's done, push, and stop (don't guess):
- A milestone needs a new dependency beyond `nicegui` and `cytoscape` CDN.
- pystructurizr lacks a needed accessor (e.g., the view-by-key lookup is missing).
- Mermaid output for a view type isn't supported by the existing generator.
- mypy --strict surfaces an issue that requires changing existing models.py.

Report which milestone you finished, what's blocking, and the branch URL.

## Verification at each milestone
- `uv run pytest` — green.
- `uv run --with mypy mypy --strict src/pystructurizr/viewer/` — clean.
- `uv run python -m pystructurizr.viewer.app` — boots, doesn't crash on the documented happy path.

## Self-pacing
- After completing and pushing a milestone, if you're well-rested, continue immediately to the next milestone.
- After M4, stop and report v0.1 to the user (natural checkpoint).
- If you sense the session is getting heavy (lots of agent fan-out, large tool outputs), schedule a wake-up in 1200–1800 seconds via the loop's pacing hook and let the conversation cool.
- Track progress with TaskCreate/TaskUpdate for the seven milestones.
