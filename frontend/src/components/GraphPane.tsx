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
  type EdgeTypes,
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
import { FloatingEdge, type FloatingEdgeData } from "./FloatingEdge";

const NODE_TYPES: NodeTypes = { element: ElementNode, boundary: BoundaryNode };
const EDGE_TYPES: EdgeTypes = { floating: FloatingEdge };

/** Relationship line routing, rendered by the floating edge. */
type EdgeStyle = "default" | "straight" | "step" | "smoothstep";

const EDGE_STYLES: { value: EdgeStyle; label: string }[] = [
  { value: "default", label: "Bezier" },
  { value: "straight", label: "Straight" },
  { value: "step", label: "Step" },
  { value: "smoothstep", label: "Smooth step" },
];

const EDGE_STYLE_STORAGE_KEY = "pystructurizr.edgeStyle";

function storedEdgeStyle(): EdgeStyle {
  const raw = window.localStorage.getItem(EDGE_STYLE_STORAGE_KEY);
  return EDGE_STYLES.some((s) => s.value === raw)
    ? (raw as EdgeStyle)
    : "default";
}

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
  onToggleExpand: (id: string, expand: boolean) => void,
): { nodes: Node[]; edges: Edge[] } {
  const anyMissingPosition = data.nodes.some((n) => n.position === undefined);
  const trail = buildTrail(view, views, workspace);
  const parentView = trail.length > 1 ? trail[trail.length - 2] : undefined;
  const boundaryType =
    view.type === "component" ? "Container" : "Software System";

  const nodes: Node[] = data.nodes.map((n) => {
    const isBoundary = n.data.kind === "boundary";
    // Only the view's own (root) boundary drills out to the parent view;
    // nested boundaries (expanded containers, deployment nodes) do not.
    const isRootBoundary = isBoundary && !n.parentId;
    const target =
      isRootBoundary && !n.data.expanded ? parentView : drillTarget(n, views);
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
        onToggleExpand,
      },
    };
  });

  const edges: Edge[] = data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: "floating",
    data: { label: e.label || undefined } satisfies FloatingEdgeData,
    markerEnd: { type: MarkerType.ArrowClosed },
  }));

  // If any node lacks a stored position, run a fresh auto-layout; otherwise
  // adapt the stored absolute positions to the nested-node model.
  const positioned = anyMissingPosition
    ? layoutGraph(nodes, edges, data.rankDirection)
    : normalizeStoredPositions(nodes, edges);
  return { nodes: positioned, edges };
}

/**
 * Renders the selected view's graph with React Flow: nested C4 boundaries
 * (to any depth — deployment nodes, expanded containers), centre-anchored
 * floating edges, draggable nodes, zoom/pan, a breadcrumb for drill in/out
 * navigation, controls and a minimap. Falls back to friendly notices for
 * unsupported/empty views and load errors.
 */
export function GraphPane({ view, views, workspace, onNavigate }: GraphPaneProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "ready">(
    "idle",
  );
  const [error, setError] = useState<string | null>(null);
  const [edgeStyle, setEdgeStyle] = useState<EdgeStyle>(storedEdgeStyle);
  // Expanded container ids, scoped to the view they were expanded in so a
  // view switch implicitly resets the expansion.
  const [expansion, setExpansion] = useState<{ key: string; ids: string[] }>({
    key: "",
    ids: [],
  });
  const expandedIds = useMemo(
    () => (view && expansion.key === view.key ? expansion.ids : []),
    [view, expansion],
  );

  const handleEdgeStyle = useCallback((style: EdgeStyle) => {
    setEdgeStyle(style);
    window.localStorage.setItem(EDGE_STYLE_STORAGE_KEY, style);
  }, []);

  const handleToggleExpand = useCallback(
    (id: string, expand: boolean) => {
      if (!view) return;
      setExpansion((prev) => {
        const ids = prev.key === view.key ? prev.ids : [];
        const next = expand ? [...ids, id] : ids.filter((x) => x !== id);
        return { key: view.key, ids: next };
      });
    },
    [view],
  );

  // Routing is presentation-only, so it is applied on the way into React
  // Flow rather than baked into the edge state.
  const styledEdges = useMemo(
    () =>
      edges.map((edge) => ({
        ...edge,
        data: { ...edge.data, pathStyle: edgeStyle },
      })),
    [edges, edgeStyle],
  );

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

    getViewGraph(view.key, expandedIds)
      .then((data) => {
        if (cancelled) return;
        const flow = toFlow(data, view, views, workspace, handleToggleExpand);
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
  }, [
    view,
    views,
    workspace,
    expandedIds,
    handleToggleExpand,
    setNodes,
    setEdges,
  ]);

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

  // Re-fit the viewport when switching views, but not on expand/collapse.
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
          context, container, component, or deployment view.
        </p>
      </div>
    );
  }

  if (status === "loading" && nodes.length === 0) {
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
        edges={styledEdges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
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
        <Panel position="top-right" className="edge-style">
          <span className="edge-style__title">Edges</span>
          {EDGE_STYLES.map((style) => (
            <button
              key={style.value}
              className={
                "edge-style__option" +
                (style.value === edgeStyle ? " edge-style__option--active" : "")
              }
              onClick={() => handleEdgeStyle(style.value)}
            >
              {style.label}
            </button>
          ))}
        </Panel>
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
