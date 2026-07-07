import { useCallback, useState } from "react";
import { getRectOfNodes, getTransformForBounds, useReactFlow } from "reactflow";
import { toPng, toSvg } from "html-to-image";

// Padding around the diagram bounds in the exported image, and a 2x pixel
// ratio for crisp PNGs on high-DPI screens.
const EXPORT_MARGIN = 40;
const PNG_SCALE = 2;
const BACKGROUND = "#f5f6f8";

type Format = "png" | "svg";

function download(dataUrl: string, filename: string): void {
  const link = document.createElement("a");
  link.href = dataUrl;
  link.download = filename;
  link.click();
}

/**
 * PNG/SVG export of the current diagram. Renders the React Flow viewport
 * (nodes, edges, labels — not the controls/minimap overlays) sized to the
 * diagram's bounding box, and downloads it named after the view key.
 *
 * Must be rendered inside the ReactFlow component so `useReactFlow` can
 * read the node bounds.
 */
export function ExportButtons({ viewKey }: { viewKey: string }) {
  const { getNodes } = useReactFlow();
  const [busy, setBusy] = useState<Format | null>(null);

  const exportAs = useCallback(
    async (format: Format) => {
      const viewport = document.querySelector<HTMLElement>(
        ".react-flow__viewport",
      );
      if (!viewport || busy) return;

      const bounds = getRectOfNodes(getNodes());
      const width = Math.ceil(bounds.width + 2 * EXPORT_MARGIN);
      const height = Math.ceil(bounds.height + 2 * EXPORT_MARGIN);
      const [x, y, zoom] = getTransformForBounds(bounds, width, height, 1, 1);

      const options = {
        backgroundColor: BACKGROUND,
        width,
        height,
        style: {
          width: `${width}px`,
          height: `${height}px`,
          transform: `translate(${x}px, ${y}px) scale(${zoom})`,
        },
      };

      setBusy(format);
      try {
        const dataUrl =
          format === "png"
            ? await toPng(viewport, { ...options, pixelRatio: PNG_SCALE })
            : await toSvg(viewport, options);
        download(dataUrl, `${viewKey}.${format}`);
      } finally {
        setBusy(null);
      }
    },
    [getNodes, viewKey, busy],
  );

  return (
    <>
      <span className="edge-style__divider" />
      {(["png", "svg"] as const).map((format) => (
        <button
          key={format}
          className="edge-style__option"
          title={`Download this diagram as ${format.toUpperCase()}`}
          disabled={busy !== null}
          onClick={() => void exportAs(format)}
        >
          {busy === format ? "…" : format.toUpperCase()}
        </button>
      ))}
    </>
  );
}
