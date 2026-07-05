interface TopBarProps {
  workspaceName: string | null;
  filePath: string | null;
}

/** Application header showing the title and the currently loaded file. */
export function TopBar({ workspaceName, filePath }: TopBarProps) {
  return (
    <header className="topbar">
      <span className="topbar__title">pystructurizr</span>
      <span className="topbar__file">
        {filePath ? (
          <>
            <strong>{workspaceName ?? filePath}</strong>
            {workspaceName ? ` — ${filePath}` : null}
          </>
        ) : (
          "No file loaded"
        )}
      </span>
    </header>
  );
}
