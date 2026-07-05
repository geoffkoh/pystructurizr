// Auto-layout for graphs whose nodes arrive without stored positions.
//
// Boundary (group) nodes make this a compound layout, which plain dagre does
// not support, so it runs in two passes:
//   1. lay out the children inside each boundary and size the boundary to
//      their bounding box (plus padding and label space);
//   2. lay out the top level, treating each boundary as one large node and
//      re-targeting cross-boundary edges to the boundary itself.

import dagre from "dagre";
import type { Edge, Node } from "reactflow";

const NODE_WIDTH = 200;
const NODE_HEIGHT = 110;
const PERSON_HEIGHT = 150;

// Space between a boundary edge and its children; the bottom pad leaves
// room for the boundary label.
const BOUNDARY_PAD_X = 28;
const BOUNDARY_PAD_TOP = 28;
const BOUNDARY_PAD_BOTTOM = 56;

interface Size {
  width: number;
  height: number;
}

interface Point {
  x: number;
  y: number;
}

function nodeSize(node: Node): Size {
  const kind = (node.data as { kind?: string } | undefined)?.kind ?? "";
  if (kind.startsWith("person")) {
    return { width: NODE_WIDTH, height: PERSON_HEIGHT };
  }
  return { width: NODE_WIDTH, height: NODE_HEIGHT };
}

/**
 * Run dagre over one level of the graph and return top-left positions.
 *
 * dagre positions nodes by their centre; React Flow positions by the
 * top-left corner, so we offset by half of each node's size.
 */
function dagreLevel(
  items: { id: string; size: Size }[],
  edges: { source: string; target: string }[],
): Map<string, Point> {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 90 });

  for (const item of items) {
    g.setNode(item.id, { ...item.size });
  }
  for (const edge of edges) {
    g.setEdge(edge.source, edge.target);
  }

  dagre.layout(g);

  const positions = new Map<string, Point>();
  for (const item of items) {
    const pos = g.node(item.id);
    positions.set(item.id, {
      x: pos.x - item.size.width / 2,
      y: pos.y - item.size.height / 2,
    });
  }
  return positions;
}

/**
 * Assign positions to all nodes, sizing boundary group nodes to fit their
 * children. Child positions are relative to their parent, as React Flow
 * expects for nested nodes.
 */
export function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  const childrenOf = new Map<string, Node[]>();
  for (const node of nodes) {
    if (node.parentNode) {
      const siblings = childrenOf.get(node.parentNode) ?? [];
      siblings.push(node);
      childrenOf.set(node.parentNode, siblings);
    }
  }

  const positions = new Map<string, Point>();
  const boundarySizes = new Map<string, Size>();

  // Pass 1: children inside each boundary, boundary sized to fit.
  for (const [parentId, children] of childrenOf) {
    const childIds = new Set(children.map((c) => c.id));
    const innerEdges = edges.filter(
      (e) => childIds.has(e.source) && childIds.has(e.target),
    );
    const laidOut = dagreLevel(
      children.map((c) => ({ id: c.id, size: nodeSize(c) })),
      innerEdges,
    );

    let maxX = 0;
    let maxY = 0;
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    for (const child of children) {
      const pos = laidOut.get(child.id)!;
      const size = nodeSize(child);
      minX = Math.min(minX, pos.x);
      minY = Math.min(minY, pos.y);
      maxX = Math.max(maxX, pos.x + size.width);
      maxY = Math.max(maxY, pos.y + size.height);
    }
    for (const child of children) {
      const pos = laidOut.get(child.id)!;
      positions.set(child.id, {
        x: pos.x - minX + BOUNDARY_PAD_X,
        y: pos.y - minY + BOUNDARY_PAD_TOP,
      });
    }
    boundarySizes.set(parentId, {
      width: maxX - minX + 2 * BOUNDARY_PAD_X,
      height: maxY - minY + BOUNDARY_PAD_TOP + BOUNDARY_PAD_BOTTOM,
    });
  }

  // Pass 2: top level, with boundaries as single large nodes and
  // cross-boundary edges lifted to the boundary.
  const parentOf = new Map<string, string>();
  for (const node of nodes) {
    if (node.parentNode) parentOf.set(node.id, node.parentNode);
  }
  const representative = (id: string) => parentOf.get(id) ?? id;

  const topNodes = nodes.filter((n) => !n.parentNode);
  const topEdgePairs = new Set<string>();
  const topEdges: { source: string; target: string }[] = [];
  for (const edge of edges) {
    const source = representative(edge.source);
    const target = representative(edge.target);
    if (source === target) continue;
    const key = `${source}->${target}`;
    if (topEdgePairs.has(key)) continue;
    topEdgePairs.add(key);
    topEdges.push({ source, target });
  }

  const topPositions = dagreLevel(
    topNodes.map((n) => ({
      id: n.id,
      size: boundarySizes.get(n.id) ?? nodeSize(n),
    })),
    topEdges,
  );
  for (const [id, pos] of topPositions) {
    positions.set(id, pos);
  }

  return nodes.map((node) => {
    const size = boundarySizes.get(node.id);
    return {
      ...node,
      position: positions.get(node.id) ?? { x: 0, y: 0 },
      ...(size ? { style: { ...node.style, ...size } } : {}),
    };
  });
}

/**
 * Adapt stored (absolute) positions to React Flow's nested-node model.
 *
 * Stored layouts predate boundaries and are absolute; children of a
 * boundary must be positioned relative to it. The boundary is re-derived
 * from its children's bounding box so stored layouts stay valid even
 * though no boundary size was ever persisted.
 */
export function normalizeStoredPositions(nodes: Node[]): Node[] {
  const childrenOf = new Map<string, Node[]>();
  for (const node of nodes) {
    if (node.parentNode) {
      const siblings = childrenOf.get(node.parentNode) ?? [];
      siblings.push(node);
      childrenOf.set(node.parentNode, siblings);
    }
  }
  if (childrenOf.size === 0) return nodes;

  const boundaryPositions = new Map<string, Point>();
  const boundarySizes = new Map<string, Size>();
  for (const [parentId, children] of childrenOf) {
    let maxX = 0;
    let maxY = 0;
    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    for (const child of children) {
      const size = nodeSize(child);
      minX = Math.min(minX, child.position.x);
      minY = Math.min(minY, child.position.y);
      maxX = Math.max(maxX, child.position.x + size.width);
      maxY = Math.max(maxY, child.position.y + size.height);
    }
    boundaryPositions.set(parentId, {
      x: minX - BOUNDARY_PAD_X,
      y: minY - BOUNDARY_PAD_TOP,
    });
    boundarySizes.set(parentId, {
      width: maxX - minX + 2 * BOUNDARY_PAD_X,
      height: maxY - minY + BOUNDARY_PAD_TOP + BOUNDARY_PAD_BOTTOM,
    });
  }

  return nodes.map((node) => {
    const asBoundary = boundaryPositions.get(node.id);
    if (asBoundary) {
      return {
        ...node,
        position: asBoundary,
        style: { ...node.style, ...boundarySizes.get(node.id)! },
      };
    }
    if (node.parentNode) {
      const parent = boundaryPositions.get(node.parentNode);
      if (parent) {
        return {
          ...node,
          position: {
            x: node.position.x - parent.x,
            y: node.position.y - parent.y,
          },
        };
      }
    }
    return node;
  });
}

export { NODE_WIDTH, NODE_HEIGHT };
