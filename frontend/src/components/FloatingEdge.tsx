import { useCallback } from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  Position,
  getBezierPath,
  getSmoothStepPath,
  getStraightPath,
  useStore,
  type EdgeProps,
  type Node,
} from "reactflow";

export interface FloatingEdgeData {
  label?: string;
  /** Which path renderer to use; anchoring is floating in all cases. */
  pathStyle?: "default" | "straight" | "step" | "smoothstep";
  /** Dynamic-view animation state for this edge's step. */
  animState?: "past" | "active" | "future";
  /** Hover-emphasis state: the hovered edge pops, the rest dim. */
  hoverState?: "hovered" | "muted";
  /** Lets the label participate in hover tracking. */
  onHoverChange?: (edgeId: string | null) => void;
}

interface Point {
  x: number;
  y: number;
}

function center(node: Node): Point {
  const { positionAbsolute, width, height } = node;
  return {
    x: (positionAbsolute?.x ?? 0) + (width ?? 0) / 2,
    y: (positionAbsolute?.y ?? 0) + (height ?? 0) / 2,
  };
}

/**
 * Point where the line from `node`'s centre towards `other`'s centre
 * crosses `node`'s rectangular border. This is what makes edges aim at
 * node centres while arrowheads still start/stop at the node edge.
 */
function borderIntersection(node: Node, other: Node): Point {
  const w = (node.width ?? 0) / 2;
  const h = (node.height ?? 0) / 2;
  const nodeCenter = center(node);
  const otherCenter = center(other);

  const dx = (otherCenter.x - nodeCenter.x) / (2 * w) || 0;
  const dy = (otherCenter.y - nodeCenter.y) / (2 * h) || 0;
  const scale = 1 / Math.max(Math.abs(dx), Math.abs(dy)) || 1;

  return {
    x: nodeCenter.x + dx * scale * w,
    y: nodeCenter.y + dy * scale * h,
  };
}

/** Which side of the node a border point sits on (for path curvature). */
function sideOf(node: Node, point: Point): Position {
  const x = node.positionAbsolute?.x ?? 0;
  const y = node.positionAbsolute?.y ?? 0;
  const width = node.width ?? 0;
  if (point.x <= x + 1) return Position.Left;
  if (point.x >= x + width - 1) return Position.Right;
  if (point.y <= y + 1) return Position.Top;
  return Position.Bottom;
}

/**
 * An edge that ignores fixed handles and anchors to node centres: the line
 * is aimed centre-to-centre and clipped to each node's border, so arrows
 * enter nodes head-on from any direction. The `pathStyle` in `data` picks
 * the renderer (bezier, straight, step, smooth step).
 */
export function FloatingEdge({
  id,
  source,
  target,
  markerEnd,
  style,
  data,
}: EdgeProps<FloatingEdgeData>) {
  const sourceNode = useStore(
    useCallback((store) => store.nodeInternals.get(source), [source]),
  );
  const targetNode = useStore(
    useCallback((store) => store.nodeInternals.get(target), [target]),
  );

  if (!sourceNode || !targetNode || !sourceNode.width || !targetNode.width) {
    return null;
  }

  const sourcePoint = borderIntersection(sourceNode, targetNode);
  const targetPoint = borderIntersection(targetNode, sourceNode);
  const params = {
    sourceX: sourcePoint.x,
    sourceY: sourcePoint.y,
    targetX: targetPoint.x,
    targetY: targetPoint.y,
    sourcePosition: sideOf(sourceNode, sourcePoint),
    targetPosition: sideOf(targetNode, targetPoint),
  };

  const pathStyle = data?.pathStyle ?? "default";
  let path: string;
  let labelX: number;
  let labelY: number;
  if (pathStyle === "straight") {
    [path, labelX, labelY] = getStraightPath({
      sourceX: params.sourceX,
      sourceY: params.sourceY,
      targetX: params.targetX,
      targetY: params.targetY,
    });
  } else if (pathStyle === "step" || pathStyle === "smoothstep") {
    [path, labelX, labelY] = getSmoothStepPath({
      ...params,
      borderRadius: pathStyle === "step" ? 0 : 8,
    });
  } else {
    [path, labelX, labelY] = getBezierPath(params);
  }

  const animState = data?.animState;
  const hoverState = data?.hoverState;
  // The hovered edge wins over everything; otherwise dynamic-view
  // animation applies, and hover-muting dims whatever is left.
  const emphasis =
    hoverState === "hovered" || animState === "active"
      ? { stroke: "#1976d2", strokeWidth: 2.4 }
      : animState === "future"
        ? { opacity: 0.08 }
        : hoverState === "muted"
          ? { opacity: 0.15 }
          : {};
  const edgeStyle = { ...style, ...emphasis };

  return (
    <>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={edgeStyle} />
      {data?.label ? (
        <EdgeLabelRenderer>
          <div
            className={
              "edge-label nodrag nopan" +
              (animState === "active" ? " edge-label--active" : "") +
              (animState === "future" ? " edge-label--future" : "") +
              (hoverState === "hovered" ? " edge-label--hovered" : "") +
              (hoverState === "muted" ? " edge-label--muted" : "")
            }
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: "all",
              zIndex: hoverState === "hovered" ? 1000 : undefined,
            }}
            onMouseEnter={() => data.onHoverChange?.(id)}
            onMouseLeave={() => data.onHoverChange?.(null)}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}
