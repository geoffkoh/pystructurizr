// Type definitions mirroring the FastAPI backend contract exactly.
// The backend (src/pystructurizr/webapp/server.py + graph.py) is the source
// of truth; keep these shapes in sync with it.

/** One entry from GET /api/views. */
export interface ViewInfo {
  key: string;
  type: string;
  title: string;
  element_id: string;
  /** Only systemContext/container/component views are renderable. */
  supported: boolean;
}

/** Response body from POST /api/load. */
export interface LoadResult {
  path: string;
  name: string;
  views: ViewInfo[];
}

/** Node kinds emitted by the graph builder (data.kind). */
export type NodeKind =
  | "person"
  | "person-external"
  | "system"
  | "system-external"
  | "container"
  | "component"
  | "boundary"
  | "infrastructure"
  | "container-instance"
  | "system-instance";

/** A React Flow node as returned by GET /api/views/{key}/graph. */
export interface GNode {
  id: string;
  data: {
    label: string;
    kind: string;
    color: string | null;
    technology: string;
    description: string;
    tags: string[];
    /** On boundary nodes: what the boundary is (e.g. "Deployment Node"). */
    boundaryLabel?: string;
    /** Tag-based style overrides (DSL styles block), when defined. */
    background?: string;
    textColor?: string;
    /** Structurizr shape name, e.g. "Cylinder", "Box", "Person". */
    shape?: string;
    /** On containers that can be expanded in place (container views). */
    expandable?: boolean;
    /** On boundary nodes produced by expanding a container. */
    expanded?: boolean;
  };
  /** Present on nodes nested inside a boundary group node. */
  parentId?: string;
  /** Usually ABSENT; when missing the frontend runs its own layout. */
  position?: { x: number; y: number };
}

/** A React Flow edge as returned by GET /api/views/{key}/graph. */
export interface GEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

/** Response body from GET /api/views/{key}/graph. */
export interface GraphData {
  nodes: GNode[];
  edges: GEdge[];
  /** dagre rank direction from the view's autoLayout: TB, BT, LR or RL. */
  rankDirection: "TB" | "BT" | "LR" | "RL";
}

/** Response body from POST /api/views/{key}/layout. */
export interface LayoutResult {
  saved: string;
}

/** Response body from GET /api/status (live-reload heartbeat). */
export interface StatusResult {
  path: string | null;
  /** Increments on every successful server-side reload. */
  generation: number;
  /** Parse error from the last failed reload; old workspace still served. */
  error: string | null;
}

// ---------------------------------------------------------------------------
// Workspace model (GET /api/workspace). Only the fields used by the element
// tree are declared strictly; the full dataclass asdict payload carries more.
// ---------------------------------------------------------------------------

export interface Person {
  id: string;
  name: string;
  description: string;
}

export interface Component {
  id: string;
  name: string;
  technology: string;
}

export interface Container {
  id: string;
  name: string;
  technology: string;
  components: Component[];
}

export interface SoftwareSystem {
  id: string;
  name: string;
  description: string;
  containers: Container[];
}

export interface Relationship {
  id: string;
  source_id: string;
  destination_id: string;
  description: string;
}

export interface WorkspaceModel {
  people: Person[];
  software_systems: SoftwareSystem[];
  relationships: Relationship[];
}

export interface Workspace {
  name: string;
  description: string;
  model: WorkspaceModel;
}
