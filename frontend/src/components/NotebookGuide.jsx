import React, { useState } from "react";
import styles from "./NotebookGuide.module.css";

export default function NotebookGuide({ runId }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const getNotebook = async () => {
    const response = await fetch(
      `/api/v1/runs/${encodeURIComponent(runId)}/export-notebook`,
    );
    if (!response.ok) {
      let message = `Notebook export failed (${response.status}).`;
      try {
        const body = await response.json();
        if (body.detail) message += ` ${body.detail}`;
      } catch {
        // Keep the HTTP status when the server did not return JSON.
      }
      if (response.status === 404) {
        message += " Restart the TrainTrace API to load the export endpoint.";
      }
      throw new Error(message);
    }
    const text = await response.text();
    let notebook;
    try {
      notebook = JSON.parse(text);
    } catch {
      throw new Error(
        "The server response is not a valid notebook. Restart the TrainTrace API and try again.",
      );
    }
    if (notebook.nbformat !== 4 || !Array.isArray(notebook.cells)) {
      throw new Error(
        notebook.detail ||
          "The server did not return a valid Jupyter notebook.",
      );
    }
    return { text, notebook };
  };

  const copyCode = async () => {
    setBusy("copy");
    setError("");
    setCopied(false);
    try {
      const { notebook } = await getNotebook();
      const code = notebook.cells
        .filter((cell) => cell.cell_type === "code")
        .map((cell) => cell.source.join(""))
        .join("\n\n# ── Next notebook cell ──\n\n");
      await navigator.clipboard.writeText(code);
      setCopied(true);
    } catch (copyError) {
      setError(copyError.message || "Could not copy the notebook code.");
    } finally {
      setBusy("");
    }
  };

  const downloadNotebook = async () => {
    setBusy("download");
    setError("");
    setCopied(false);
    try {
      const { text } = await getNotebook();
      const url = URL.createObjectURL(
        new Blob([text], { type: "application/x-ipynb+json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `traintrace_${runId}.ipynb`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (downloadError) {
      setError(downloadError.message || "Notebook download failed.");
    } finally {
      setBusy("");
    }
  };

  return (
    <details className={styles.guide}>
      <summary>Take this run to Colab or Jupyter</summary>
      <div className={styles.content}>
        <p>
          Copy the runnable code into Colab/Jupyter, or download the complete
          notebook. Both include this run’s settings, model, preprocessing,
          training loop, charts, and metric/checkpoint saving code.
        </p>
        <div className={styles.actions}>
          <button
            type="button"
            className={`${styles.action} ${styles.primary}`}
            onClick={copyCode}
            disabled={Boolean(busy)}
          >
            {busy === "copy" ? "Copying code…" : "Copy notebook code"}
          </button>
          <button
            type="button"
            className={`${styles.action} ${styles.secondary}`}
            onClick={downloadNotebook}
            disabled={Boolean(busy)}
          >
            {busy === "download" ? "Preparing file…" : "Download .ipynb"}
          </button>
        </div>
        {copied && (
          <p className={styles.success} role="status">
            Code copied. Paste it into a Colab or Jupyter code cell.
          </p>
        )}
        {error && (
          <p className={styles.error} role="alert">
            {error}
          </p>
        )}
        <p className={styles.note}>
          Copy the code into a notebook cell, or upload the .ipynb file to
          Colab/Jupyter. Either starts a fresh training run; its results do not
          sync back into TrainTrace. Final test evaluation is opt-in.
        </p>
      </div>
    </details>
  );
}
