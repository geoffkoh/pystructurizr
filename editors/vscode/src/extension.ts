import * as vscode from "vscode";

import { PreviewManager } from "./preview";

export function activate(context: vscode.ExtensionContext): void {
  const previews = new PreviewManager();
  context.subscriptions.push(previews);

  context.subscriptions.push(
    vscode.commands.registerCommand("pystructurizr.openPreview", async () => {
      const document = vscode.window.activeTextEditor?.document;
      if (!document || document.languageId !== "structurizr-dsl") {
        void vscode.window.showInformationMessage(
          "pystructurizr: open a Structurizr DSL file (.dsl) first.",
        );
        return;
      }
      if (document.isDirty) await document.save();
      await previews.open(document);
    }),
  );
}

export function deactivate(): void {
  // Disposal (server shutdown) happens via context.subscriptions.
}
