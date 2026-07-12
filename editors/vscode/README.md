# pystructurizr for VS Code

Structurizr DSL support in VS Code, powered by
[pystructurizr](https://github.com/geoffkoh/pystructurizr).

## Features

- **Syntax highlighting** for `.dsl` / `.structurizr` files: element and
  view keywords, style properties, `!include`/`!docs`/`!adrs` directives
  with their paths, strings, comments, `#hex` colours, `->`
  relationships, `alias =` definitions. The grammar mirrors the token
  spec used by the web app's source viewer
  (`frontend/src/highlight.ts`).
- **Language basics**: comment toggling, brace/quote auto-close,
  indentation on `{`.
- *(Coming in part 2)* Interactive C4 diagram preview in a webview — the
  full pystructurizr React Flow app (drag layouts, in-place expansion,
  themes and cloud-provider icons, filtered views, live reload on save)
  against a locally spawned server.

## Development

No build step is needed for the language features (the grammar is
declarative). To try it:

1. Open `editors/vscode/` in VS Code.
2. Press `F5` (Run Extension) — an Extension Development Host opens.
3. Open any sample, e.g. `samples/hedge_fund/workspace.dsl`.

Packaging as an installable `.vsix` arrives with part 3.
