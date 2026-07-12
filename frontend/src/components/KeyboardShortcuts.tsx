import { useEffect } from "react";
import { useReactFlow } from "reactflow";

import { exportDiagram } from "../export";
import { isTypingTarget } from "../shortcuts";

interface KeyboardShortcutsProps {
  viewKey: string;
  /** Toggles the hover-emphasis feature (the toolbar's Hover button). */
  onHoverToggle: () => void;
}

/**
 * Graph-scoped keyboard shortcuts: `f` fits the diagram to the window,
 * `p`/`s` export PNG/SVG, `h` toggles hover emphasis. Renders nothing;
 * must sit inside the ReactFlow component for `useReactFlow`. App-level
 * shortcuts (view navigation, help overlay) live in App.tsx.
 */
export function KeyboardShortcuts({
  viewKey,
  onHoverToggle,
}: KeyboardShortcutsProps) {
  const { fitView, getNodes } = useReactFlow();

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (isTypingTarget(event.target)) return;
      switch (event.key) {
        case "f":
          fitView({ duration: 250, padding: 0.15 });
          break;
        case "p":
          void exportDiagram(getNodes(), viewKey, "png");
          break;
        case "s":
          void exportDiagram(getNodes(), viewKey, "svg");
          break;
        case "h":
          onHoverToggle();
          break;
        default:
          return;
      }
      event.preventDefault();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [fitView, getNodes, viewKey, onHoverToggle]);

  return null;
}
