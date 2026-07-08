import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError, getSource } from "../api";
import { highlightDsl } from "../highlight";
import type { SourceResult } from "../types";

export interface CodeFocus {
  elementId: string;
  /** Changes on every request so re-focusing the same element re-flashes. */
  nonce: number;
}

interface SourcePaneProps {
  /** Bumped by the app whenever a live reload refreshed the workspace. */
  reloadTick: number;
  focus: CodeFocus | null;
}

/**
 * Read-only DSL source viewer: the workspace's files (root plus !include
 * fragments) listed on the left, syntax-highlighted content with line
 * numbers on the right. When `focus` names an element, the pane switches
 * to its defining file, scrolls the definition into view and flashes the
 * line.
 */
export function SourcePane({ reloadTick, focus }: SourcePaneProps) {
  const [data, setData] = useState<SourceResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [flash, setFlash] = useState<{ line: number; nonce: number } | null>(
    null,
  );
  const codeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getSource()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
        setSelectedPath(
          (previous) =>
            previous && result.files.some((f) => f.path === previous)
              ? previous
              : (result.files[0]?.path ?? null),
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Failed to load source");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadTick]);

  // Apply an element focus once the source is available.
  useEffect(() => {
    if (!focus || !data) return;
    const location = data.locations[focus.elementId];
    if (!location) return;
    setSelectedPath(location.path);
    setFlash({ line: location.line, nonce: focus.nonce });
  }, [focus, data]);

  // Scroll the flashed line into view after it renders.
  useEffect(() => {
    if (!flash) return;
    const line = codeRef.current?.querySelector(`[data-line="${flash.line}"]`);
    line?.scrollIntoView({ block: "center" });
  }, [flash, selectedPath]);

  const file = data?.files.find((f) => f.path === selectedPath) ?? null;
  const lines = useMemo(
    () => (file ? highlightDsl(file.content) : []),
    [file],
  );

  if (error) {
    return (
      <div className="notice">
        <div className="notice__title">Could not load the source</div>
        <p>{error}</p>
      </div>
    );
  }

  if (!data || !file) {
    return (
      <div className="notice">
        <div className="notice__title">No source loaded</div>
        <p>Load a DSL workspace to browse its files.</p>
      </div>
    );
  }

  return (
    <div className="docs">
      <nav className="docs__toc">
        {data.files.map((entry) => (
          <button
            key={entry.path}
            className={
              "docs__toc-item" +
              (entry.path === selectedPath ? " docs__toc-item--active" : "")
            }
            onClick={() => setSelectedPath(entry.path)}
          >
            {entry.path}
          </button>
        ))}
      </nav>
      <div className="src" ref={codeRef}>
        {lines.map((spans, index) => {
          const lineNumber = index + 1;
          const focused =
            flash !== null &&
            flash.line === lineNumber &&
            data.locations[focus?.elementId ?? ""]?.path === selectedPath;
          return (
            <div
              key={focused ? `focus-${flash.nonce}` : lineNumber}
              data-line={lineNumber}
              className={"src__line" + (focused ? " src__line--focus" : "")}
            >
              <span className="src__lineno">{lineNumber}</span>
              <span className="src__text">
                {spans.length === 0
                  ? " "
                  : spans.map((span, spanIndex) =>
                      span.cls ? (
                        <span key={spanIndex} className={`dsl-${span.cls}`}>
                          {span.text}
                        </span>
                      ) : (
                        span.text
                      ),
                    )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
