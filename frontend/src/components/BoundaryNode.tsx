import { memo, type MouseEvent } from "react";
import type { NodeProps } from "reactflow";

export interface BoundaryNodeData {
  label: string;
  kind: string;
  technology: string;
  /** What the boundary is: "Software System", "Container", "Deployment Node". */
  boundaryLabel?: string;
  /** Fallback used when the backend sends no boundaryLabel. */
  boundaryType: string;
  /** Set when this boundary is an in-place-expanded container. */
  expanded?: boolean;
  /** Key of the parent view to navigate to on double-click, if any. */
  drillKey?: string;
  drillLabel?: string;
  onToggleExpand?: (id: string, expand: boolean) => void;
}

/**
 * The dashed C4 boundary that groups the scoped element's children (also
 * used for deployment nodes and in-place-expanded containers). Sized by
 * the layout (via node style); the label sits bottom-left per Structurizr
 * convention. The view's own boundary drills up a level on double-click;
 * expanded containers show a − control to collapse them.
 */
function BoundaryNodeComponent({ id, data }: NodeProps<BoundaryNodeData>) {
  const typeLabel = data.boundaryLabel ?? data.boundaryType;
  const meta = data.technology ? `${typeLabel}: ${data.technology}` : typeLabel;
  const collapsible = Boolean(data.expanded && data.onToggleExpand);

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
      <div className="boundary__label">
        {data.label}
        <span className="boundary__type">[{meta}]</span>
      </div>
      {collapsible ? (
        <button
          className="boundary__collapse"
          title="Collapse back to a container"
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
