# Enterprise roadmap (parked phases)

The staged plan for making pystructurizr an enterprise-grade,
**local-first** solution-architect toolset (no multi-user server/auth;
team sharing happens via git and generated artifacts). Phase 1 shipped in
July 2026 — Jira PP-60…PP-63, PRs #38–#41: workspace JSON export with
structurizr round-trip, remote themes + cloud-provider icons + the full
shape set, filtered views, and keyboard shortcuts.

Phases 2–4 below are parked while the VS Code integration
(`editors/vscode/`) is built. Value ratings come from a
solution-architect review of real workflows (solution reviews,
governance boards, CABs, onboarding). Complexity: S ≤ 1 ticket,
M = 1–2, L = 3+ / new subsystem.

The structural insight behind the ordering: the three genuinely
differentiating features — **model lint in CI, diagram diff on PRs, and
impact analysis** — all fall out of two shared foundations, a public
**model-query layer** (Phase 2) and **headless rendering** (Phase 3).
Build each foundation once, harvest it repeatedly. The metamodel already
carries `properties` and `perspectives` on every element, so the
governance and overlay features are UI/reporting work, not model work.

## Phase 2 — Foundation A: model-query layer → model intelligence

| Feature | Value | Cx | Notes |
|---|---|---|---|
| **Public query layer + CLI** — `pystructurizr query` over elements/relationships/tags/properties, JSON/CSV out, transitive closure | High (enabler) | M | New `model/query.py`. Everything below consumes it; feeds scripts/CMDB sync. The filtered-view tag predicate (PP-62) is its seed. |
| **Model lint/validation** — orphans, missing description/technology, duplicate relationships, naming conventions; configurable ruleset; CLI exit code for CI | High | M | `pystructurizr lint`; rules as small classes. How standards get enforced without review bottlenecks. |
| **Full-model explorer + search** — whole-model graph page + element/relationship search across all `!include` fragments | High | M-L | Reuse React Flow + dagre (no new deps); jump from a result to the views containing the element. |
| **Governance inventory** — owner/team/lifecycle from element `properties` in the UI + CMDB/tech-radar report (HTML/CSV) | High | M | `pystructurizr inventory`; makes the model the system of record. |

## Phase 3 — Foundation B: headless rendering → docs-as-code

| Feature | Value | Cx | Notes |
|---|---|---|---|
| **Headless CI rendering** — `pystructurizr render` → SVG/PNG/Mermaid for all views, no browser | High (enabler) | L | Server-side SVG reusing `view_graph.py` semantics; layout engine choice (Python dagre-equivalent vs small Node script) to be raised per the no-new-deps rule. |
| **Static HTML site export** — self-contained site (diagrams + docs + ADRs + inventory) for any static host/Confluence | High | M-L | *The* sharing story for a local-first tool. Must embed fetched theme icons as data URIs. |
| **Diagram diff** — two git revisions compared: added/removed/changed elements & relationships per view, visual overlay + text report | High | L | `pystructurizr diff rev1 rev2` for PR comments; model diff on the query layer, overlay via the renderer. |

## Phase 4 — Differentiators & authoring depth

| Feature | Value | Cx | Notes |
|---|---|---|---|
| **Impact analysis** — transitive dependents/dependencies + affected views for a chosen element | High | M | The most-asked change-advisory-board question; query-layer walk + UI highlight mode. |
| **Perspectives overlays** — security/data/infra per-element overlays | Med-High | M | Parsed already; toolbar overlay selector + badge/tint rendering. |
| **Workspace composition / landscape roll-up** — stitch per-team workspaces (`extends`/federation) into one enterprise landscape | High | L | The real "enterprise" scope gap; align DSL semantics with upstream `extends`. |
| **ADR workflow tooling** — CLI create/supersede, ADR↔element links, status dashboard | Med | M | Templates + git already cover much; links add traceability. |
| **In-browser DSL editor** — diagnostics + element-id autocomplete | Med | L | Live reload + external editor already tight; needs an editor component dep (ask first). |
| **Scaffolding** — `pystructurizr init` org templates; deterministic diff-friendly layout sidecars | Med | S-M | Onboarding ergonomics. |

**Parked as low value:** manual edge vertices (auto-layout + curve
separation already solve edge readability; hand-placed vertices rot on
every model change).

**Open chore:** PP-50 — vite/esbuild upgrade for the frontend's npm audit
advisories.

## Delivery conventions (unchanged)

One Jira ticket per item, branch per ticket, PR-first merge, wait for
merge before the next ticket. TDD; `uv run pytest` + ruff + mypy green
per PR; no new Python/npm dependencies without asking; live verification
on the sample workspaces; update `docs/structurizr-parity.md` as items
land.
