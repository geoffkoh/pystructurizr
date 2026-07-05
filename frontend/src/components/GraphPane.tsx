import { useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";

import { ApiError, getViewGraph } from "../api";
import { layoutGraph } from "../layout";
import type { GraphData, ViewInfo } from "../types";
import { ElementNode, type ElementNodeData } from "./ElementNode";

const NODE_TYPES: NodeTypes = { element: ElementNode };

interface GraphPaneProps {
  view: ViewInfo | null;
}

/** Convert the API graph payload into React Flow nodes/edges. */
function toFlow(data: GraphData): { nodes: Node<ElementNodeData>[]; edges: Edge[] } {
  const anyMissingPosition = data.nodes.some((n) => n.position === undefined);

  const nodes: Node<ElementNodeData>[] = data.nodes.map((n) => ({
    id: n.id,
    type: "element",
    position: n.position ?? { x: 0, y: 0 },
    data: n.data,
  }));

  const edges: Edge[] = data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label || undefined,
    markerEnd: { type: MarkerType.ArrowClosed },
  }));

  // If any node lacks a stored position, run a fresh top-down auto-layout.
  const positioned = anyMissingPosition ? layoutGraph(nodes, edges) : nodes;
  return { nodes: positioned as Node<ElementNodeData>[], edges };
}

/**
 * Renders the selected view's graph with React Flow: draggable nodes,
 * zoom/pan, controls and a minimap. Falls back to friendly notices for
 * unsupported/empty views and load errors.
 */
export function GraphPane({ view }: GraphPaneProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<ElementNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "ready">(
    "idle",
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!view || !view.supported) {
      setNodes([]);
      setEdges([]);
      setStatus("idle");
      setError(null);
      return;
    }

    let cancelled = false;
    setStatus("loading");
    setError(null);

    getViewGraph(view.key)
      .then((data) => {
        if (cancelled) return;
        const flow = toFlow(data);
        setNodes(flow.nodes);
        setEdges(flow.edges);
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError ? err.message : "Failed to load graph";
        setError(message);
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [view, setNodes, setEdges]);

  const isEmpty = status === "ready" && nodes.length === 0;

  // Stable fitView key so the viewport re-fits when the graph changes.
  const fitKey = useMemo(() => view?.key ?? "none", [view]);

  if (!view) {
    return (
      <div className="notice">
        <div className="notice__title">No view selected</div>
        <p>Choose a renderable view from the sidebar to see its diagram.</p>
      </div>
    );
  }

  if (!view.supported) {
    return (
      <div className="notice">
        <div className="notice__title">This view is not renderable yet</div>
        <p>
          <code>{view.type}</code> views are not supported. Try a system
          context, container, or component view.
        </p>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="notice">
        <div className="notice__title">Loading diagram…</div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="notice">
        <div className="notice__title">Could not load this diagram</div>
        <p>{error}</p>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="notice">
        <div className="notice__title">Nothing to show</div>
        <p>This view has no elements to display.</p>
      </div>
    );
  }

  return (
    <div className="graph">
      <ReactFlow
        key={fitKey}
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        minZoom={0.1}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} />
        <Controls />
        <MiniMap
          pannable
          zoomable
          nodeColor={(n) => {
            const data = n.data as ElementNodeData | undefined;
            return data?.color ?? "#78909c";
          }}
        />
      </ReactFlow>
    </div>
  );
}
