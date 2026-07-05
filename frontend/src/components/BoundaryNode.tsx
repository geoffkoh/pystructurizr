import { memo } from "react";
import type { NodeProps } from "reactflow";

export interface BoundaryNodeData {
  label: string;
  kind: string;
  /** "Software System" in container views, "Container" in component views. */
  boundaryType: string;
  /** Key of the parent view to navigate to on double-click, if any. */
  drillKey?: string;
  drillLabel?: string;
}

/**
 * The dashed C4 boundary that groups the scoped element's children. Sized
 * by the layout (via node style); the label sits bottom-left per
 * Structurizr convention. Double-click navigates up a level when a parent
 * view exists.
 */
function BoundaryNodeComponent({ data }: NodeProps<BoundaryNodeData>) {
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
        <span className="boundary__type">[{data.boundaryType}]</span>
      </div>
    </div>
  );
}

export const BoundaryNode = memo(BoundaryNodeComponent);
