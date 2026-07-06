// Drill-in/out navigation between C4 abstraction levels.
//
// Views are related through their element_id: a system's context view sits
// above its container view, which sits above the component views of its
// containers. These helpers resolve those relationships so the graph pane
// can offer double-click drill-in and a breadcrumb trail for drill-out.

import type { GNode, ViewInfo, Workspace } from "./types";

const TYPE_LABELS: Record<string, string> = {
  systemContext: "Context",
  container: "Containers",
  component: "Components",
  deployment: "Deployment",
};

function findView(
  views: ViewInfo[],
  type: string,
  elementId: string,
): ViewInfo | undefined {
  return views.find(
    (v) => v.supported && v.type === type && v.element_id === elementId,
  );
}

/** Name of the model element with the given id, if it exists. */
export function elementName(
  workspace: Workspace | null,
  id: string,
): string | null {
  if (!workspace) return null;
  for (const person of workspace.model.people) {
    if (person.id === id) return person.name;
  }
  for (const system of workspace.model.software_systems) {
    if (system.id === id) return system.name;
    for (const container of system.containers) {
      if (container.id === id) return container.name;
      for (const component of container.components) {
        if (component.id === id) return component.name;
      }
    }
  }
  return null;
}

/** Short breadcrumb label for a view, e.g. "Internet Banking · Containers". */
export function crumbLabel(
  view: ViewInfo,
  workspace: Workspace | null,
): string {
  const name = elementName(workspace, view.element_id);
  const level = TYPE_LABELS[view.type] ?? view.type;
  return name ? `${name} · ${level}` : view.title || view.key;
}

/** The view a node drills into on double-click, if one exists. */
export function drillTarget(
  node: GNode,
  views: ViewInfo[],
): ViewInfo | undefined {
  if (node.data.kind === "system") {
    return findView(views, "container", node.id);
  }
  if (node.data.kind === "container") {
    return findView(views, "component", node.id);
  }
  return undefined;
}

/**
 * Breadcrumb trail from the top abstraction level down to `view`.
 *
 * Only levels with an actual matching view appear; the current view is
 * always last.
 */
export function buildTrail(
  view: ViewInfo,
  views: ViewInfo[],
  workspace: Workspace | null,
): ViewInfo[] {
  if (view.type === "container") {
    const context = findView(views, "systemContext", view.element_id);
    return context ? [context, view] : [view];
  }
  if (view.type === "component" && workspace) {
    const system = workspace.model.software_systems.find((s) =>
      s.containers.some((c) => c.id === view.element_id),
    );
    if (!system) return [view];
    const context = findView(views, "systemContext", system.id);
    const containers = findView(views, "container", system.id);
    return [
      ...(context ? [context] : []),
      ...(containers ? [containers] : []),
      view,
    ];
  }
  return [view];
}
