import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";

/** Colour used when the backend supplies no palette colour for a kind. */
const FALLBACK_COLOR = "#78909c";

/** C4 metadata label per element kind, shown as `[Container: Java]`. */
const KIND_LABELS: Record<string, string> = {
  person: "Person",
  "person-external": "Person",
  system: "Software System",
  "system-external": "Software System",
  container: "Container",
  component: "Component",
};

export interface ElementNodeData {
  label: string;
  kind: string;
  color: string | null;
  technology: string;
  description: string;
  tags: string[];
  /** Key of the view this node drills into on double-click, if any. */
  drillKey?: string;
  /** Label of the drill target, used for the hover hint. */
  drillLabel?: string;
}

function metaLine(data: ElementNodeData): string {
  const kindLabel = KIND_LABELS[data.kind] ?? data.kind;
  return data.technology ? `[${kindLabel}: ${data.technology}]` : `[${kindLabel}]`;
}

/**
 * Custom React Flow node coloured by its element kind. People render with
 * the conventional C4 silhouette (head circle above the box); all elements
 * show their `[Kind: technology]` metadata and description. Nodes with a
 * drill target show an affordance and open it on double-click.
 */
function ElementNodeComponent({ data }: NodeProps<ElementNodeData>) {
  const background = data.color ?? FALLBACK_COLOR;
  const isPerson = data.kind.startsWith("person");
  const drillable = Boolean(data.drillKey);

  const box = (
    <div
      className={
        "node" +
        (isPerson ? " node--person" : "") +
        (drillable ? " node--drillable" : "")
      }
      style={{ background }}
      title={
        drillable ? `Double-click to open ${data.drillLabel ?? "view"}` : undefined
      }
    >
      <Handle type="target" position={Position.Top} />
      <div className="node__label">{data.label}</div>
      <div className="node__kind">{metaLine(data)}</div>
      {data.description ? (
        <div className="node__desc">{data.description}</div>
      ) : null}
      {drillable ? <div className="node__drill">⊕</div> : null}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );

  if (!isPerson) return box;

  return (
    <div className="person">
      <div className="person__head" style={{ background }} />
      {box}
    </div>
  );
}

export const ElementNode = memo(ElementNodeComponent);
