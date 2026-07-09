// Lightweight Structurizr DSL syntax highlighter.
//
// No mainstream highlighter ships a Structurizr grammar, so this mirrors
// the backend parser's tokenizer (dsl.py _TOKEN_RE) and classifies tokens
// into a handful of span classes rendered by the source viewer. Block
// comments may span lines; the output is therefore per-line span arrays.

export interface HighlightSpan {
  text: string;
  /** CSS modifier (comment, string, color, keyword, def, arrow, directive, number) or null for plain text. */
  cls: string | null;
}

const KEYWORDS = new Set([
  "workspace",
  "model",
  "views",
  "person",
  "softwaresystem",
  "container",
  "component",
  "deploymentnode",
  "infrastructurenode",
  "softwaresysteminstance",
  "containerinstance",
  "deploymentenvironment",
  "enterprise",
  "group",
  "systemlandscape",
  "systemcontext",
  "dynamic",
  "deployment",
  "filtered",
  "styles",
  "element",
  "relationship",
  "theme",
  "themes",
  "branding",
  "terminology",
]);

const PROPERTIES = new Set([
  "include",
  "exclude",
  "autolayout",
  "background",
  "color",
  "colour",
  "stroke",
  "shape",
  "border",
  "icon",
  "fontsize",
  "opacity",
  "width",
  "height",
  "thickness",
  "dashed",
]);

// Whitespace must be its own token and the punctuation catch-all a SINGLE
// character: a greedy multi-char catch-all would swallow the whitespace
// together with the `"`, `//`, `->`, `#` or `!` that starts the next
// token, leaving strings/comments/arrows/colours/directives unhighlighted.
const TOKEN_RE =
  /\/\*[\s\S]*?\*\/|\/\/[^\n]*|"(?:[^"\\]|\\.)*"|#[0-9A-Fa-f]{3,8}|->|![A-Za-z]+|[A-Za-z_][A-Za-z0-9_]*|[0-9]+|\n|[ \t]+|[^\nA-Za-z0-9_]/g;

function classify(text: string, nextSolid: string | undefined): string | null {
  if (text.startsWith("//") || text.startsWith("/*")) return "comment";
  if (text.startsWith('"')) return "string";
  if (/^#[0-9A-Fa-f]{3,8}$/.test(text)) return "color";
  if (text === "->") return "arrow";
  if (text.startsWith("!")) return "directive";
  if (/^[0-9]+$/.test(text)) return "number";
  if (/^[A-Za-z_]/.test(text)) {
    const lower = text.toLowerCase();
    if (KEYWORDS.has(lower)) return "keyword";
    if (PROPERTIES.has(lower)) return "property";
    if (nextSolid === "=") return "def";
    return null;
  }
  return null;
}

/**
 * Highlight DSL source into one span array per line. Newlines are never
 * part of a span; multi-line tokens (block comments) are split across
 * their lines with the same class.
 */
export function highlightDsl(source: string): HighlightSpan[][] {
  const raw = source.match(TOKEN_RE) ?? [];

  // Look ahead to the next non-whitespace token so `name =` identifiers
  // can be styled as definitions.
  const solids: (string | undefined)[] = new Array(raw.length);
  let next: string | undefined;
  for (let i = raw.length - 1; i >= 0; i--) {
    solids[i] = next;
    const trimmed = raw[i].trim();
    if (trimmed !== "" && raw[i] !== "\n") next = trimmed;
  }

  const lines: HighlightSpan[][] = [[]];
  // After a !directive, the rest of the line is a path/argument: suppress
  // keyword/definition colouring there (`!include model/oms.dsl` must not
  // paint "model" as a keyword).
  let inDirectiveLine = false;
  raw.forEach((token, index) => {
    if (token === "\n") {
      lines.push([]);
      inDirectiveLine = false;
      return;
    }
    let cls = classify(token, solids[index]);
    if (cls === "directive") {
      inDirectiveLine = true;
    } else if (
      inDirectiveLine &&
      (cls === "keyword" || cls === "property" || cls === "def")
    ) {
      cls = null;
    }
    const parts = token.split("\n");
    parts.forEach((part, partIndex) => {
      if (partIndex > 0) lines.push([]);
      if (part !== "") lines[lines.length - 1].push({ text: part, cls });
    });
  });
  return lines;
}
