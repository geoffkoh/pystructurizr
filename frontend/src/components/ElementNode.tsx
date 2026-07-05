import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

/** Colour used when the backend supplies no palette colour for a kind. */
const FALLBACK_COLOR = "#78909c";

export interface ElementNodeData {
  label: string;
  kind: string;
  color: string | null;
}

/**
 * Custom React Flow node coloured by its element kind, showing the label
 * with a small kind sub-label underneath.
 */
function ElementNodeComponent({ data }: NodeProps<ElementNodeData>) {
  const background = data.color ?? FALLBACK_COLOR;
  return (
    <div className="node" style={{ background }}>
      <Handle type="target" position={Position.Top} />
      <div className="node__label">{data.label}</div>
      {data.kind ? <div className="node__kind">{data.kind}</div> : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}

export const ElementNode = memo(ElementNodeComponent);
