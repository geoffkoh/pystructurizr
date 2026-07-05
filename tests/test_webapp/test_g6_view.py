"""Tests for the g6_view graph-data helper reused by the web app."""

from __future__ import annotations

from pathlib import Path

from pystructurizr.parser.dsl import parse_dsl_file
from pystructurizr.webapp.g6_view import apply_positions, to_g6_data

FIXTURE = Path(__file__).parent.parent / "fixtures" / "example.dsl"


def test_to_g6_data_has_nodes_and_edges() -> None:
    ws = parse_dsl_file(FIXTURE)
    view = ws.views[0]
    data = to_g6_data(ws, view)
    assert data["nodes"], "expected visible nodes for the first view"
    assert all("id" in n and "data" in n for n in data["nodes"])


def test_apply_positions_round_trip() -> None:
    ws = parse_dsl_file(FIXTURE)
    view = ws.views[0]
    # Pick two visible node ids from the generated graph so the test does
    # not depend on the specific identifiers in the fixture.
    ids = [n["id"] for n in to_g6_data(ws, view)["nodes"]][:2]
    assert len(ids) == 2

    apply_positions(view, {ids[0]: (100, 200), ids[1]: (300, 400)})
    assert len(view.element_views) == 2

    data = to_g6_data(ws, view)
    positioned = {
        node["id"]: node["style"]
        for node in data["nodes"]
        if "style" in node and "x" in node["style"]
    }
    assert positioned[ids[0]] == {"x": 100, "y": 200}
    assert positioned[ids[1]] == {"x": 300, "y": 400}
