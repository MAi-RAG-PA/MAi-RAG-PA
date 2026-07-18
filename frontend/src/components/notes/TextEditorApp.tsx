// frontend/src/components/notes/TextEditorApp.tsx
import React, { useState, useRef } from "react";
import apiClient from "../../api/client";

const ACCEPTED_TYPES = ".txt,.md,.py,.js,.ts,.json,.yaml,.yml,.toml,.html,.css,.sql,.sh,.csv,.xml,.ini,.cfg,.log";

const TextEditorApp: React.FC = () => {
  const [content, setContent] = useState("");
  const [fileName, setFileName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [fileHandle, setFileHandle] = useState<FileSystemFileHandle | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fallbackInputRef = useRef<HTMLInputElement>(null);

  const handleOpenFile = async () => {
    if ("showOpenFilePicker" in window) {
      try {
        const [handle] = await (window as any).showOpenFilePicker({
          types: [
            {
              description: "Text & Code Files",
              accept: {
                "text/*": ACCEPTED_TYPES.split(",").map((ext) => ext.trim()),
              },
            },
          ],
          multiple: false,
        });

        setFileHandle(handle);
        const file = await handle.getFile();
        setFileName(file.name);
        setContent(await file.text());
      } catch (err: any) {
        if (err.name !== "AbortError") {
          console.error("Failed to open file:", err);
          alert("Could not open file. Falling back to standard picker.");
          fallbackInputRef.current?.click();
        }
      }
    } else {
      fallbackInputRef.current?.click();
    }
  };

  const handleFallbackChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      setContent(event.target?.result as string);
      setFileName(file.name);
      setFileHandle(null);
    };
    reader.readAsText(file);

    if (fallbackInputRef.current) {
      fallbackInputRef.current.value = "";
    }
  };

  const handleSave = async () => {
    const trimmedName = fileName.trim();

    if (!trimmedName) {
      alert("Please enter a filename with extension (e.g., notes.txt)");
      return;
    }
    if (!trimmedName.includes(".")) {
      alert("Filename must include an extension (e.g., .txt, .md, .py)");
      return;
    }

    setIsLoading(true);
    try {
      if (fileHandle) {
        const writable = await fileHandle.createWritable();
        await writable.write(content);
        await writable.close();
        alert(`✓ Saved directly to: ${trimmedName}`);
      } else {
        await apiClient.post("/api/notes/save", {
          filename: trimmedName,
          content,
        });
        alert(`✓ Saved to workspace: ${trimmedName}\n(Note: Direct save requires Chrome/Edge/Vivaldi)`);
      }
    } catch (error: any) {
      console.error("Save failed:", error);
      alert(`Failed to save: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setContent("");
    setFileName("");
    setFileHandle(null);
    textareaRef.current?.focus();
  };

  const handleTabInsert = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Tab") return;

    e.preventDefault();
    const textarea = e.currentTarget;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    const nextValue = value.substring(0, start) + "  " + value.substring(end);

    textarea.value = nextValue;
    textarea.selectionStart = textarea.selectionEnd = start + 2;
    setContent(nextValue);
  };

  return (
    <section
      className="console reveal delay-2 notes-panel"
      role="region"
      aria-label="Text Editor"
      style={{
        padding: 20,
        background: "rgba(15,20,29,0.95)",
        borderRadius: 16,
        border: "2px solid var(--accent, #7cf6d3)",
        boxShadow: "0 0 20px rgba(124, 246, 211, 0.3)",
        color: "var(--text, #e0e0e0)",
        width: "100%",
        boxSizing: "border-box",
      }}
    >
      <input
        ref={fallbackInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        onChange={handleFallbackChange}
        style={{ display: "none" }}
        aria-hidden="true"
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: "var(--accent, #7cf6d3)" }}>Text Editor</h3>
        <span style={{ fontSize: "0.8rem", opacity: 0.7 }} role="status" aria-live="polite">
          {content.length} chars
          {fileHandle && <span style={{ color: "var(--accent)" }}> • Direct Save Ready</span>}
        </span>
      </div>

      <textarea
        ref={textareaRef}
        placeholder="Start typing your notes..."
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onKeyDown={handleTabInsert}
        spellCheck={true}
        aria-label="Note content editor"
        aria-describedby="editor-help"
        style={{
          width: "100%",
          minHeight: 200,
          maxHeight: 600,
          padding: 12,
          borderRadius: 12,
          border: "1px solid var(--line, rgba(255,255,255,0.12))",
          background: "rgba(255,255,255,0.04)",
          color: "var(--text, #e0e0e0)",
          fontSize: "1rem",
          fontFamily: "monospace",
          resize: "vertical",
          outline: "none",
          boxSizing: "border-box",
          whiteSpace: "pre-wrap",
        }}
      />

      <div
        style={{ marginTop: 16, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}
        role="group"
        aria-label="Editor controls"
      >
        <button
          type="button"
          onClick={handleClear}
          className="chip"
          aria-label="Clear all content"
          style={{
            padding: "10px 16px",
            borderRadius: 12,
            backgroundColor: "rgba(255,255,255,0.08)",
            color: "var(--text)",
            border: "1px solid var(--line)",
            cursor: "pointer",
            fontWeight: 500,
            fontSize: "0.9rem",
          }}
        >
          Clear
        </button>

        <button
          type="button"
          onClick={handleOpenFile}
          className="chip"
          aria-label="Open file from computer"
          style={{
            padding: "10px 16px",
            borderRadius: 12,
            backgroundColor: "rgba(255,255,255,0.08)",
            color: "var(--text)",
            border: "1px solid var(--line)",
            cursor: "pointer",
            fontWeight: 500,
            fontSize: "0.9rem",
          }}
        >
          Open File
        </button>

        <label htmlFor="filename-input" style={{ display: "none" }}>
          File Name
        </label>
        <input
          id="filename-input"
          type="text"
          placeholder="Edit & Save Opened File, or Create New File with supported Extensions: .txt .md .css .html .log .py .js .sh .json .yaml .yml .toml .sql .csv .xml .ts .ini .cfg"
          value={fileName}
          onChange={(e) => setFileName(e.target.value)}
          aria-label="File name with extension"
          aria-required="true"
          style={{
            flexGrow: 1,
            minWidth: 200,
            padding: "10px 14px",
            borderRadius: 12,
            border: "1px solid var(--line)",
            background: "rgba(255,255,255,0.04)",
            color: "var(--text)",
            fontSize: "0.95rem",
            outline: "none",
          }}
        />

        <button
          onClick={handleSave}
          disabled={isLoading}
          className="btn"
          aria-label={isLoading ? "Saving file" : "Save file to disk"}
          style={{
            padding: "10px 24px",
            borderRadius: 12,
            backgroundColor: isLoading ? "rgba(255,255,255,0.1)" : "var(--accent, #7cf6d3)",
            color: isLoading ? "#666" : "#000",
            border: "none",
            cursor: isLoading ? "not-allowed" : "pointer",
            fontWeight: 600,
            fontSize: "0.95rem",
          }}
        >
          {isLoading ? "Saving..." : "Save File"}
        </button>
      </div>

      <div
        id="editor-help"
        style={{ marginTop: 8, fontSize: "0.75rem", opacity: 0.6, lineHeight: 1.4 }}
        role="note"
        aria-label="Editor usage tips"
      >
        <strong>Tip:</strong> In Chrome/Edge/Vivaldi, opened files save back to their original location.
        In Firefox, files save to ~/MAi-RAG-PA/workspace/.
      </div>
    </section>
  );
};

export default TextEditorApp;
