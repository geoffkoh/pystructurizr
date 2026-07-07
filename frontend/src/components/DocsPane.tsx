import { useEffect, useMemo, useState } from "react";
import { marked } from "marked";

import type { DocDecision, DocSection, Workspace } from "../types";

export type DocsMode = "documentation" | "decisions";

interface DocsPaneProps {
  workspace: Workspace | null;
  mode: DocsMode;
}

/**
 * Render workspace markdown to HTML.
 *
 * The content comes from files on the user's own disk (a local tool), so
 * no additional sanitisation is applied beyond what marked does.
 */
function renderMarkdown(content: string): string {
  return marked.parse(content, { async: false });
}

const STATUS_CLASSES: Record<string, string> = {
  accepted: "docs__status--accepted",
  proposed: "docs__status--proposed",
  superseded: "docs__status--superseded",
  deprecated: "docs__status--superseded",
  rejected: "docs__status--superseded",
};

function statusClass(status: string): string {
  const key = Object.keys(STATUS_CLASSES).find((k) =>
    status.toLowerCase().startsWith(k),
  );
  return key ? STATUS_CLASSES[key] : "";
}

/**
 * Long-form documentation and ADR reader: a table of contents on the left
 * and the selected markdown document on the right. Sections come from
 * `!docs` directories, decisions from `!adrs` (with status/date metadata).
 */
export function DocsPane({ workspace, mode }: DocsPaneProps) {
  const sections: DocSection[] = workspace?.documentation.sections ?? [];
  const decisions: DocDecision[] = workspace?.documentation.decisions ?? [];
  const items = mode === "documentation" ? sections : decisions;
  const [selected, setSelected] = useState(0);

  useEffect(() => {
    setSelected(0);
  }, [mode, workspace]);

  const current = items[Math.min(selected, Math.max(items.length - 1, 0))];
  const html = useMemo(
    () => (current ? renderMarkdown(current.content) : ""),
    [current],
  );

  if (!workspace || items.length === 0) {
    return (
      <div className="notice">
        <div className="notice__title">
          {mode === "documentation" ? "No documentation" : "No decisions"}
        </div>
        <p>
          Attach markdown with{" "}
          <code>{mode === "documentation" ? "!docs <dir>" : "!adrs <dir>"}</code>{" "}
          in the workspace DSL.
        </p>
      </div>
    );
  }

  return (
    <div className="docs">
      <nav className="docs__toc">
        {items.map((item, index) => (
          <button
            key={index}
            className={
              "docs__toc-item" +
              (index === selected ? " docs__toc-item--active" : "")
            }
            onClick={() => setSelected(index)}
          >
            {mode === "decisions" && "id" in item ? `${item.id}. ` : ""}
            {item.title}
            {mode === "decisions" && "status" in item && item.status ? (
              <span className={`docs__status ${statusClass(item.status)}`}>
                {item.status}
              </span>
            ) : null}
          </button>
        ))}
      </nav>
      <article className="docs__content">
        {mode === "decisions" && current && "date" in current && current.date ? (
          <div className="docs__meta">{current.date}</div>
        ) : null}
        <div
          className="docs__markdown"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </article>
    </div>
  );
}
