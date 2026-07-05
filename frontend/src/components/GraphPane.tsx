import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  Panel,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
  type NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";

import { ApiError, getViewGraph } from "../api";
import { layoutGraph, normalizeStoredPositions } from "../layout";
import { buildTrail, crumbLabel, drillTarget } from "../navigation";
import type { GraphData, ViewInfo, Workspace } from "../types";
import { BoundaryNode } from "./BoundaryNode";
import { ElementNode, type ElementNodeData } from "./ElementNode";

const NODE_TYPES: NodeTypes = { element: ElementNode, boundary: BoundaryNode };

interface GraphPaneProps {
  view: ViewInfo | null;
  views: ViewInfo[];
  workspace: Workspace | null;
  onNavigate: (view: ViewInfo) => void;
}

/** Convert the API graph payload into React Flow nodes/edges. */
function toFlow(
  data: GraphData,
  view: ViewInfo,
  views: ViewInfo[],
  workspace: Workspace | null,
): { nodes: Node[]; edges: Edge[] } {
  const anyMissingPosition = data.nodes.some((n) => n.position === undefined);
  const trail = buildTrail(view, views, workspace);
  const parentView = trail.length > 1 ? trail[trail.length - 2] : undefined;
  const boundaryType =
    view.type === "component" ? "Container" : "Software System";

  const nodes: Node[] = data.nodes.map((n) => {
    const isBoundary = n.data.kind === "boundary";
    // Boundaries drill out to the parent view; systems/containers drill in.
    const target = isBoundary ? parentView : drillTarget(n, views);
    return {
      id: n.id,
      type: isBoundary ? "boundary" : "element",
      position: n.position ?? { x: 0, y: 0 },
      ...(n.parentId
        ? { parentNode: n.parentId, extent: "parent" as const }
        : {}),
      selectable: !isBoundary,
      data: {
        ...n.data,
        boundaryType,
        drillKey: target?.key,
        drillLabel: target ? crumbLabel(target, workspace) : undefined,
      },
    };
  });

  const edges: Edge[] = data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label || undefined,
    markerEnd: { type: MarkerType.ArrowClosed },
  }));

  // If any node lacks a stored position, run a fresh auto-layout; otherwise
  // adapt the stored absolute positions to the nested-node model.
  const positioned = anyMissingPosition
    ? layoutGraph(nodes, edges)
    : normalizeStoredPositions(nodes);
  return { nodes: positioned, edges };
}

/**
 * Renders the selected view's graph with React Flow: nested C4 boundaries,
 * draggable nodes, zoom/pan, a breadcrumb for drill in/out navigation,
 * controls and a minimap. Falls back to friendly notices for
 * unsupported/empty views and load errors.
 */
export function GraphPane({ view, views, workspace, onNavigate }: GraphPaneProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
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
        const flow = toFlow(data, view, views, workspace);
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
  }, [view, views, workspace, setNodes, setEdges]);

  const handleNodeDoubleClick = useCallback(
    (_event: unknown, node: Node) => {
      const key = (node.data as ElementNodeData | undefined)?.drillKey;
      if (!key) return;
      const target = views.find((v) => v.key === key);
      if (target) onNavigate(target);
    },
    [views, onNavigate],
  );

  const trail = useMemo(
    () => (view ? buildTrail(view, views, workspace) : []),
    [view, views, workspace],
  );

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
        onNodeDoubleClick={handleNodeDoubleClick}
        fitView
        minZoom={0.1}
        proOptions={{ hideAttribution: true }}
      >
        {trail.length > 1 ? (
          <Panel position="top-left" className="breadcrumb">
            {trail.map((crumb, index) => (
              <span key={crumb.key} className="breadcrumb__item">
                {index > 0 ? <span className="breadcrumb__sep">›</span> : null}
                {crumb.key === view.key ? (
                  <span className="breadcrumb__crumb breadcrumb__crumb--current">
                    {crumbLabel(crumb, workspace)}
                  </span>
                ) : (
                  <button
                    className="breadcrumb__crumb"
                    onClick={() => onNavigate(crumb)}
                  >
                    {crumbLabel(crumb, workspace)}
                  </button>
                )}
              </span>
            ))}
          </Panel>
        ) : null}
        <Background gap={16} />
        <Controls />
        <MiniMap
          pannable
          zoomable
          nodeColor={(n) => {
            const data = n.data as ElementNodeData | undefined;
            if (data?.kind === "boundary") return "rgba(144, 164, 174, 0.25)";
            return data?.color ?? "#78909c";
          }}
        />
      </ReactFlow>
    </div>
  );
}
