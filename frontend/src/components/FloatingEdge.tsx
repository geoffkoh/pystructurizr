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
  /** Set on the hovered edge so it pops; other edges are unaffected. */
  hoverState?: "hovered";
  /** Lets the label participate in hover tracking. */
  onHoverChange?: (edgeId: string | null) => void;
  /**
   * Perpendicular offset (px) separating edges that share a node pair
   * (bidirectional flows, parallel relationships): the edge bows through
   * a control point this far from the centre line, and its label sits on
   * the curve's apex. Absent/0 keeps the straight centre line.
   */
  curveOffset?: number;
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
 * Point where the line from `node`'s centre towards `aimAt` crosses
 * `node`'s rectangular border. This is what makes edges aim at node
 * centres (or a curve's control point) while arrowheads still start and
 * stop at the node edge.
 */
function borderIntersection(node: Node, aimAt: Point): Point {
  const w = (node.width ?? 0) / 2;
  const h = (node.height ?? 0) / 2;
  const nodeCenter = center(node);

  const dx = (aimAt.x - nodeCenter.x) / (2 * w) || 0;
  const dy = (aimAt.y - nodeCenter.y) / (2 * h) || 0;
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
 * the renderer (bezier, straight, step, smooth step); a `curveOffset`
 * bows the edge sideways so overlapping relationships fan apart.
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

  const sourceCenter = center(sourceNode);
  const targetCenter = center(targetNode);
  const curveOffset = data?.curveOffset ?? 0;

  // With an offset, everything aims at a control point perpendicular to
  // the centre line's midpoint instead of the other node's centre.
  let control: Point | null = null;
  if (curveOffset !== 0) {
    const dx = targetCenter.x - sourceCenter.x;
    const dy = targetCenter.y - sourceCenter.y;
    const length = Math.hypot(dx, dy) || 1;
    control = {
      x: (sourceCenter.x + targetCenter.x) / 2 + (-dy / length) * curveOffset,
      y: (sourceCenter.y + targetCenter.y) / 2 + (dx / length) * curveOffset,
    };
  }

  const sourcePoint = borderIntersection(sourceNode, control ?? targetCenter);
  const targetPoint = borderIntersection(targetNode, control ?? sourceCenter);
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
  if (control && (pathStyle === "default" || pathStyle === "straight")) {
    // Quadratic bezier through the offset control point; the label sits
    // on the curve's apex, Q(0.5) = 0.25·S + 0.5·C + 0.25·T.
    path = `M ${sourcePoint.x},${sourcePoint.y} Q ${control.x},${control.y} ${targetPoint.x},${targetPoint.y}`;
    labelX = 0.25 * sourcePoint.x + 0.5 * control.x + 0.25 * targetPoint.x;
    labelY = 0.25 * sourcePoint.y + 0.5 * control.y + 0.25 * targetPoint.y;
  } else if (pathStyle === "straight") {
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
      ...(control ? { centerX: control.x, centerY: control.y } : {}),
    });
  } else {
    [path, labelX, labelY] = getBezierPath(params);
  }

  const animState = data?.animState;
  const hovered = data?.hoverState === "hovered";
  // The hovered edge pops (colour, weight, glow); nothing else changes.
  // Dynamic-view animation still dims future steps.
  const emphasis = hovered
    ? {
        stroke: "#1976d2",
        strokeWidth: 2.6,
        filter: "drop-shadow(0 0 3px rgba(25, 118, 210, 0.55))",
      }
    : animState === "active"
      ? { stroke: "#1976d2", strokeWidth: 2.4 }
      : animState === "future"
        ? { opacity: 0.08 }
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
              (hovered ? " edge-label--hovered" : "")
            }
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: "all",
              zIndex: hovered ? 1000 : undefined,
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
