import { useCallback, useEffect, useState } from "react";

import { ApiError, getWorkspace, listFiles, listViews, loadFile } from "./api";
import type { ViewInfo, Workspace } from "./types";
import { ElementTree } from "./components/ElementTree";
import { FilePicker } from "./components/FilePicker";
import { GraphPane } from "./components/GraphPane";
import { TopBar } from "./components/TopBar";
import { ViewList } from "./components/ViewList";

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
    Promise.all([getWorkspace(), listViews()])
      .then(([ws, vs]) => {
        if (cancelled) return;
        setWorkspace(ws);
        setViews(vs);
      })
      .catch(() => {
        // 409 (nothing loaded yet) is expected; ignore.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSelectFile = useCallback(async (path: string) => {
    setLoadingPath(path);
    setError(null);
    try {
      const result = await loadFile(path);
      setCurrentPath(result.path);
      setViews(result.views);
      setSelectedView(null);
      const ws = await getWorkspace();
      setWorkspace(ws);
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
          <GraphPane view={selectedView} />
        </main>
      </div>
    </div>
  );
}
