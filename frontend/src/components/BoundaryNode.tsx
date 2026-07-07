import { memo, useCallback, type MouseEvent } from "react";
import { NodeResizer, useStore, type NodeProps } from "reactflow";

// A resized boundary must always enclose its children (plus breathing room
// and label space) and never collapse below a sensible floor.
const MIN_WIDTH = 220;
const MIN_HEIGHT = 140;
const CHILD_PAD_X = 28;
const CHILD_PAD_BOTTOM = 56;

export interface BoundaryNodeData {
  label: string;
  kind: string;
  technology: string;
  /** What the boundary is: "Software System", "Container", "Deployment Node". */
  boundaryLabel?: string;
  /** Fallback used when the backend sends no boundaryLabel. */
  boundaryType: string;
  /** Set when this boundary is an in-place-expanded element. */
  expanded?: boolean;
  /** Key of the parent view to navigate to on double-click, if any. */
  drillKey?: string;
  drillLabel?: string;
  onToggleExpand?: (id: string, expand: boolean) => void;
  /** Called after the user finishes resizing, so the layout can be saved. */
  onGeometryChange?: () => void;
}

/**
 * The dashed C4 boundary that groups the scoped element's children (also
 * used for deployment nodes, the enterprise, and in-place-expanded
 * elements). Sized by the layout (via node style); the label sits
 * bottom-left per Structurizr convention. Selecting the boundary shows
 * resize handles whose minimum always encloses the children. The view's
 * own boundary drills up a level on double-click; expanded elements show
 * a − control to collapse them.
 */
function BoundaryNodeComponent({ id, data, selected }: NodeProps<BoundaryNodeData>) {
  const typeLabel = data.boundaryLabel ?? data.boundaryType;
  const meta = data.technology ? `${typeLabel}: ${data.technology}` : typeLabel;
  const collapsible = Boolean(data.expanded && data.onToggleExpand);

  // Minimum size that keeps every (possibly dragged) child inside.
  const minSize = useStore(
    useCallback(
      (store) => {
        let width = MIN_WIDTH;
        let height = MIN_HEIGHT;
        store.nodeInternals.forEach((node) => {
          if (node.parentNode !== id) return;
          width = Math.max(
            width,
            node.position.x + (node.width ?? 0) + CHILD_PAD_X,
          );
          height = Math.max(
            height,
            node.position.y + (node.height ?? 0) + CHILD_PAD_BOTTOM,
          );
        });
        return { width, height };
      },
      [id],
    ),
    (a, b) => a.width === b.width && a.height === b.height,
  );

  const handleCollapse = (event: MouseEvent) => {
    event.stopPropagation();
    data.onToggleExpand?.(id, false);
  };

  return (
    <div
      className="boundary"
      title={
        data.drillKey
          ? `Double-click to go up to ${data.drillLabel ?? "the parent view"}`
          : undefined
      }
    >
      <NodeResizer
        isVisible={selected}
        minWidth={minSize.width}
        minHeight={minSize.height}
        lineClassName="boundary__resize-line"
        handleClassName="boundary__resize-handle"
        onResizeEnd={() => data.onGeometryChange?.()}
      />
      <div className="boundary__label">
        {data.label}
        <span className="boundary__type">[{meta}]</span>
      </div>
      {collapsible ? (
        <button
          className="boundary__collapse"
          title="Collapse back in place"
          onClick={handleCollapse}
          onDoubleClick={(event) => event.stopPropagation()}
        >
          −
        </button>
      ) : null}
    </div>
  );
}

export const BoundaryNode = memo(BoundaryNodeComponent);
