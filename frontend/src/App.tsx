import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  getStatus,
  getWorkspace,
  listFiles,
  listViews,
  loadFile,
} from "./api";
import type { ViewInfo, Workspace } from "./types";
import { ElementTree } from "./components/ElementTree";
import { FilePicker } from "./components/FilePicker";
import { GraphPane } from "./components/GraphPane";
import { TopBar } from "./components/TopBar";
import { ViewList } from "./components/ViewList";

/** How often to ask the server whether the loaded source changed on disk. */
const RELOAD_POLL_MS = 2000;

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export default function App() {
  const [files, setFiles] = useState<string[]>([]);
  const [currentPath, setCurrentPath] = useState<string | null>(null);
  const [loadingPath, setLoadingPath] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [views, setViews] = useState<ViewInfo[]>([]);
  const [selectedView, setSelectedView] = useState<ViewInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadError, setReloadError] = useState<string | null>(null);
  const generationRef = useRef(0);

  // Load the file list once on mount.
  useEffect(() => {
    listFiles()
      .then(setFiles)
      .catch((err: unknown) =>
        setError(errorMessage(err, "Failed to list files")),
      );
  }, []);

  // If a workspace is already loaded server-side, hydrate the UI on mount.
  useEffect(() => {
    let cancelled = false;
    Promise.all([getWorkspace(), listViews(), getStatus()])
      .then(([ws, vs, status]) => {
        if (cancelled) return;
        setWorkspace(ws);
        setViews(vs);
        setCurrentPath(status.path);
        generationRef.current = status.generation;
      })
      .catch(() => {
        // 409 (nothing loaded yet) is expected; ignore.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /** Refetch workspace + views after a server-side live reload. */
  const refresh = useCallback(async () => {
    const [ws, vs] = await Promise.all([getWorkspace(), listViews()]);
    setWorkspace(ws);
    setViews(vs);
    // Keep the current view selected by key; a fresh object identity makes
    // the graph pane refetch. Deselect if the view no longer exists.
    setSelectedView((previous) =>
      previous ? (vs.find((v) => v.key === previous.key) ?? null) : null,
    );
  }, []);

  // Live reload: poll the server; when its generation changes the source
  // was edited on disk and successfully reloaded.
  useEffect(() => {
    if (!currentPath) return;
    const timer = window.setInterval(() => {
      getStatus()
        .then((status) => {
          setReloadError(status.error);
          if (status.generation !== generationRef.current) {
            generationRef.current = status.generation;
            void refresh();
          }
        })
        .catch(() => {
          // Server briefly unreachable (e.g. restart); try again next tick.
        });
    }, RELOAD_POLL_MS);
    return () => window.clearInterval(timer);
  }, [currentPath, refresh]);

  const handleSelectFile = useCallback(async (path: string) => {
    setLoadingPath(path);
    setError(null);
    setReloadError(null);
    try {
      const result = await loadFile(path);
      setCurrentPath(result.path);
      setViews(result.views);
      setSelectedView(null);
      const [ws, status] = await Promise.all([getWorkspace(), getStatus()]);
      setWorkspace(ws);
      generationRef.current = status.generation;
    } catch (err) {
      setError(errorMessage(err, "Failed to load file"));
    } finally {
      setLoadingPath(null);
    }
  }, []);

  return (
    <div className="app">
      <TopBar workspaceName={workspace?.name ?? null} filePath={currentPath} />
      <div className="body">
        <aside className="sidebar">
          {error ? <div className="error">{error}</div> : null}
          {reloadError ? (
            <div className="error">
              <strong>Live reload paused:</strong> {reloadError}
            </div>
          ) : null}
          <FilePicker
            files={files}
            currentPath={currentPath}
            loadingPath={loadingPath}
            onSelect={handleSelectFile}
          />
          <ViewList
            views={views}
            selectedKey={selectedView?.key ?? null}
            onSelect={setSelectedView}
          />
          <ElementTree workspace={workspace} />
        </aside>
        <main className="main">
          <GraphPane
            view={selectedView}
            views={views}
            workspace={workspace}
            onNavigate={setSelectedView}
          />
        </main>
      </div>
    </div>
  );
}
