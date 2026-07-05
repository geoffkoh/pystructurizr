"""FastAPI backend for the pystructurizr React web application.

This package exposes a small JSON API that lets a single-page frontend
browse Structurizr sources on disk, load a workspace, enumerate its views
and fetch React Flow-shaped graph data for the supported view types
(``systemContext``, ``container`` and ``component``).

The NiceGUI viewers under :mod:`pystructurizr.web` and
:mod:`pystructurizr.viewer` are left untouched; this backend is an
independent, additive feature.
"""

from __future__ import annotations
