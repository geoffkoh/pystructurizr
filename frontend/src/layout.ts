// Auto-layout for graphs whose nodes arrive without stored positions.
// Uses dagre to produce a clean top-down hierarchical layout.

import dagre from "dagre";
import type { Edge, Node } from "reactflow";

const NODE_WIDTH = 190;
const NODE_HEIGHT = 70;

/**
 * Assign positions to nodes using a dagre top-down layout.
 *
 * dagre positions nodes by their centre; React Flow positions by the
 * top-left corner, so we offset by half the node size.
 */
export function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 90 });

  for (const node of nodes) {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  return nodes.map((node) => {
    const pos = g.node(node.id);
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    };
  });
}

export { NODE_WIDTH, NODE_HEIGHT };
