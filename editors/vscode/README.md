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
- **Interactive C4 diagram preview**: the "Pystructurizr: Open Diagram
  Preview" command (also a button in the editor title bar of DSL files)
  opens the full pystructurizr React Flow app beside your editor — view
  sidebar, drag layouts, in-place expansion, themes and cloud-provider
  icons, filtered views, dynamic-view animation, keyboard shortcuts.
  Saving the DSL file (or any `!include` fragment) refreshes the preview
  automatically within ~2 seconds.

## How the preview works

The extension spawns a local `pystructurizr webapp` server for the file
(bound to `127.0.0.1` on a free port) and embeds it in a webview. The
server is killed when the preview panel closes. Its logs go to the
"pystructurizr" output channel.

Requirements: a Python environment that can run pystructurizr. By
default the server is launched with `uv run pystructurizr` from your
workspace folder; change the `pystructurizr.serverCommand` setting if
you use a venv or a global install (e.g. `["pystructurizr"]`).

## Development

1. `npm install && npm run compile` in `editors/vscode/`.
2. Open `editors/vscode/` in VS Code and press `F5` (Run Extension).
3. In the Extension Development Host, open
   `samples/hedge_fund/workspace.dsl` and click the preview icon in the
   editor title bar.

Packaging as an installable `.vsix` arrives with part 3.
