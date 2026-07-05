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
  | "boundary";

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
}

/** Response body from POST /api/views/{key}/layout. */
export interface LayoutResult {
  saved: string;
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
