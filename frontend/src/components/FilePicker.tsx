interface FilePickerProps {
  files: string[];
  currentPath: string | null;
  loadingPath: string | null;
  onSelect: (path: string) => void;
}

/** Lists available source files; clicking one loads that workspace. */
export function FilePicker({
  files,
  currentPath,
  loadingPath,
  onSelect,
}: FilePickerProps) {
  return (
    <section className="section">
      <h2 className="section__title">Files</h2>
      {files.length === 0 ? (
        <p className="muted">No source files found.</p>
      ) : (
        <ul className="list">
          {files.map((file) => {
            const isActive = file === currentPath;
            const isLoading = file === loadingPath;
            return (
              <li key={file}>
                <button
                  type="button"
                  className={
                    "list__item" + (isActive ? " list__item--active" : "")
                  }
                  onClick={() => onSelect(file)}
                  disabled={loadingPath !== null}
                  title={file}
                >
                  <span>{file}</span>
                  {isLoading ? <span className="badge">loading…</span> : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
