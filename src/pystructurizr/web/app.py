"""NiceGUI-based web viewer for pystructurizr."""

from __future__ import annotations

from pystructurizr.generators.mermaid import MermaidGenerator
from pystructurizr.models import Workspace


def run_app(workspace: Workspace, host: str = "127.0.0.1", port: int = 8080) -> None:
    from nicegui import ui

    generator = MermaidGenerator(workspace)
    diagrams = generator.generate_all()
    view_keys = list(diagrams.keys())

    def _render_mermaid(diagram: str) -> str:
        escaped = diagram.replace("`", "\\`").replace("$", "\\$")
        return f"""(async () => {{
          const {{ default: mermaid }} = await import('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs');
          mermaid.initialize({{ startOnLoad: false, theme: 'default' }});
          const container = document.getElementById('mermaid-container');
          try {{
            const {{ svg }} = await mermaid.render('mermaid-' + Date.now(), `{escaped}`);
            container.innerHTML = svg;
          }} catch(e) {{
            container.innerText = 'Render error: ' + e.message;
          }}
        }})();"""

    @ui.page('/')
    def index():
        current_key: dict = {"key": view_keys[0] if view_keys else ""}
        source_area: dict = {}

        def select_view(key: str) -> None:
            current_key["key"] = key
            ui.run_javascript(_render_mermaid(diagrams[key]))
            if "source" in source_area:
                source_area["source"].set_content(
                    f"<pre style='font-size:0.75rem;white-space:pre-wrap'>{diagrams[key]}</pre>"
                )

        with ui.header().classes("bg-blue-800 text-white"):
            ui.label("pystructurizr").classes("text-xl font-bold")
            ui.label(workspace.name or "Workspace").classes("ml-4 opacity-80")

        with ui.left_drawer().classes("bg-gray-100 p-2"):
            ui.label("Views").classes("font-semibold text-gray-700 mb-2")
            for key in view_keys:
                view = next((v for v in workspace.views if v.key == key), None)
                label = view.title or key if view else key
                ui.button(label, on_click=lambda k=key: select_view(k)).classes(
                    "w-full text-left mb-1"
                )

        initial_diagram = diagrams.get(current_key["key"], "")

        with ui.column().classes("w-full p-4"):
            with ui.tabs() as tabs:
                diagram_tab = ui.tab("Diagram")
                source_tab = ui.tab("Mermaid Source")

            with ui.tab_panels(tabs, value=diagram_tab).classes("w-full"):
                with ui.tab_panel(diagram_tab):
                    ui.html('<div id="mermaid-container" style="width:100%;overflow:auto;"></div>').classes("w-full")
                    ui.timer(0, lambda: ui.run_javascript(_render_mermaid(initial_diagram)), once=True)
                with ui.tab_panel(source_tab):
                    src_elem = ui.html(
                        f"<pre style='font-size:0.75rem;white-space:pre-wrap'>{initial_diagram}</pre>"
                    ).classes("w-full")
                    source_area["source"] = src_elem

    ui.run(host=host, port=port, title="pystructurizr", reload=False)
