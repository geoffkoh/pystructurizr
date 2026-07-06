"""FastAPI application factory and JSON API for the React web app.

The API is intentionally thin: it browses Structurizr sources under a root
directory, loads a selected workspace into :class:`AppState`, and serves
view metadata plus React Flow graph data. All mutable state lives on
``app.state`` (via dependency injection) so there are no module-level
globals.
"""

from __future__ import annotations

import dataclasses
import importlib.resources
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pystructurizr.models import View, Workspace
from pystructurizr.webapp.g6_view import apply_positions
from pystructurizr.webapp import graph
from pystructurizr.webapp.loader import WorkspaceLoadError, load_workspace


_SOURCE_SUFFIXES = frozenset({".dsl", ".json", ".structurizr"})
_SKIP_DIRS = frozenset({"node_modules", ".venv", "__pycache__"})
_MAX_DEPTH = 5


@dataclass
class AppState:
    """Mutable server state, stored on ``app.state``.

    Attributes:
        root: The directory sources are browsed and resolved within.
        current_path: The absolute path of the currently loaded source, if any.
        workspace: The currently loaded workspace, if any.
        diagrams: Per-view-key cache of computed React Flow graph data.
    """

    root: Path
    current_path: Path | None = None
    workspace: Workspace | None = None
    diagrams: dict[str, dict[str, Any]] = field(default_factory=dict)


class LoadRequest(BaseModel):
    """Body for ``POST /api/load``."""

    path: str


class LayoutRequest(BaseModel):
    """Body for ``POST /api/views/{key}/layout``."""

    positions: dict[str, tuple[int, int]]


def _get_state(request: Request) -> AppState:
    """Return the :class:`AppState` attached to the running app."""
    state: AppState = request.app.state.app_state
    return state


def _require_workspace(state: AppState) -> Workspace:
    """Return the loaded workspace or raise 409 if none is loaded."""
    if state.workspace is None:
        raise HTTPException(status_code=409, detail="No workspace loaded")
    return state.workspace


def _safe_resolve(root: Path, rel: str) -> Path:
    """Resolve ``rel`` under ``root``, rejecting traversal and bad suffixes.

    Args:
        root: The directory that resolved paths must stay within.
        rel: A relative path supplied by the client.

    Returns:
        The resolved absolute path.

    Raises:
        HTTPException: 400 if the path escapes ``root`` or has an unsupported
            suffix.
    """
    candidate = (root / rel).resolve()
    if not candidate.is_relative_to(root):
        raise HTTPException(status_code=400, detail="Path escapes the root directory")
    if candidate.suffix.lower() not in _SOURCE_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {candidate.suffix or '(none)'}",
        )
    return candidate


def _find_view(workspace: Workspace, key: str) -> View:
    """Return the view with ``key`` or raise 404."""
    for view in workspace.views:
        if view.key == key:
            return view
    raise HTTPException(status_code=404, detail=f"Unknown view key: {key}")


def _views_index(workspace: Workspace) -> list[dict[str, Any]]:
    """Return the serialisable index of all views in ``workspace``."""
    return [
        {
            "key": view.key,
            "type": view.type.value,
            "title": view.title,
            "element_id": view.element_id,
            "supported": graph.is_supported(view),
        }
        for view in workspace.views
    ]


_WORKSPACE_RE = re.compile(r"^\s*workspace\b", re.MULTILINE)


def _is_workspace_root(path: Path) -> bool:
    """Whether a source file defines a workspace of its own.

    DSL sources split across files via ``!include`` contain fragment files
    (elements/relationships only) that cannot be loaded standalone; only
    files declaring a ``workspace`` block are offered in the browser. JSON
    exports are always complete workspaces.
    """
    if path.suffix.lower() == ".json":
        return True
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            head = handle.read(8192)
    except OSError:
        return False
    return _WORKSPACE_RE.search(head) is not None


def _iter_source_files(root: Path) -> list[str]:
    """Return POSIX-relative paths of loadable source files under ``root``.

    Recurses up to ``_MAX_DEPTH`` levels, skipping hidden directories,
    well-known noise directories (``node_modules``, ``.venv`` ...) and DSL
    fragment files that only exist to be ``!include``-ed.
    """
    found: list[str] = []

    def walk(directory: Path, depth: int) -> None:
        if depth > _MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name.startswith(".") or entry.name in _SKIP_DIRS:
                    continue
                walk(entry, depth + 1)
            elif entry.suffix.lower() in _SOURCE_SUFFIXES and _is_workspace_root(entry):
                found.append(entry.relative_to(root).as_posix())

    walk(root, 0)
    return found


def create_app(
    root: Path, initial: Path | None = None, static_dir: Path | None = None
) -> FastAPI:
    """Build the FastAPI app serving the web backend.

    Args:
        root: Directory that sources are browsed and resolved within.
        initial: Optional source to load eagerly on startup.
        static_dir: Directory holding the built SPA. When ``None`` the
            packaged ``pystructurizr/webapp/static`` directory is used.

    Returns:
        A configured :class:`fastapi.FastAPI` instance.
    """
    root = root.resolve()
    app = FastAPI(title="pystructurizr webapp")
    state = AppState(root=root)

    if initial is not None:
        initial = initial.resolve()
        state.workspace = load_workspace(initial)
        state.current_path = initial

    app.state.app_state = state

    @app.get("/api/files")
    def list_files(state: AppState = Depends(_get_state)) -> list[str]:
        """List relative paths of all source files under the root."""
        return _iter_source_files(state.root)

    @app.post("/api/load")
    def load(
        body: LoadRequest, state: AppState = Depends(_get_state)
    ) -> dict[str, Any]:
        """Load the workspace at the given relative path."""
        path = _safe_resolve(state.root, body.path)
        try:
            workspace = load_workspace(path)
        except WorkspaceLoadError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        state.workspace = workspace
        state.current_path = path
        state.diagrams.clear()
        return {
            "path": path.relative_to(state.root).as_posix(),
            "name": workspace.name,
            "views": _views_index(workspace),
        }

    @app.get("/api/workspace")
    def get_workspace(state: AppState = Depends(_get_state)) -> dict[str, Any]:
        """Return the full loaded workspace as a JSON-safe dict."""
        workspace = _require_workspace(state)
        return dataclasses.asdict(workspace)

    @app.get("/api/views")
    def get_views(state: AppState = Depends(_get_state)) -> list[dict[str, Any]]:
        """Return the index of all views in the loaded workspace."""
        workspace = _require_workspace(state)
        return _views_index(workspace)

    @app.get("/api/views/{key}/graph")
    def get_view_graph(
        key: str, expand: str = "", state: AppState = Depends(_get_state)
    ) -> dict[str, Any]:
        """Return React Flow graph data for the view with ``key``.

        ``expand`` is an optional comma-separated list of container ids to
        expand in place (container views only).
        """
        workspace = _require_workspace(state)
        expand_ids = {part for part in expand.split(",") if part}
        cache_key = f"{key}::{','.join(sorted(expand_ids))}"
        if cache_key in state.diagrams:
            return state.diagrams[cache_key]
        view = _find_view(workspace, key)
        data = graph.view_graph(workspace, view, expand_ids or None)
        state.diagrams[cache_key] = data
        return data

    @app.post("/api/views/{key}/layout")
    def save_layout(
        key: str, body: LayoutRequest, state: AppState = Depends(_get_state)
    ) -> dict[str, str]:
        """Persist node positions for a view to a sidecar layout JSON file."""
        workspace = _require_workspace(state)
        view = _find_view(workspace, key)
        apply_positions(view, dict(body.positions))
        for cached in [k for k in state.diagrams if k.split("::")[0] == key]:
            state.diagrams.pop(cached)

        if state.current_path is not None:
            out_path = state.current_path.with_name(
                f"{state.current_path.stem}.layout.json"
            )
        else:
            out_path = state.root / "workspace.json"
        out_path.write_text(
            json.dumps(dataclasses.asdict(workspace), indent=2),
            encoding="utf-8",
        )
        return {"saved": str(out_path)}

    _mount_static(app, static_dir)
    return app


def _mount_static(app: FastAPI, static_dir: Path | None) -> None:
    """Mount the built SPA, or expose a hint if it is not built yet.

    Args:
        app: The application to mount static assets on.
        static_dir: Directory holding the built SPA. When ``None`` the
            packaged ``pystructurizr/webapp/static`` directory is used.
    """
    if static_dir is None:
        static_dir = Path(
            str(importlib.resources.files("pystructurizr.webapp") / "static")
        )
    if static_dir.is_dir():
        app.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True),
            name="spa",
        )
    else:

        @app.get("/")
        def spa_not_built() -> dict[str, str]:
            """Explain that the frontend bundle is missing."""
            return {"detail": "frontend not built - run npm run build in frontend/"}


def run_server(root: Path, initial: Path | None, host: str, port: int) -> None:
    """Run the web backend with uvicorn.

    Args:
        root: Directory sources are browsed and resolved within.
        initial: Optional source to load eagerly on startup.
        host: Interface to bind to.
        port: TCP port to listen on.
    """
    import uvicorn

    uvicorn.run(create_app(root, initial), host=host, port=port, log_level="info")
