// frontend/src/components/memory/LongTermMemoryApp.tsx
import React, { useState, useRef, useEffect } from "react";
import apiClient from "../../api/client";

const LongTermMemoryApp: React.FC = () => {
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("");
  const [newCollectionName, setNewCollectionName] = useState("");
  const [mode, setMode] = useState<"select" | "create">("select");

  const [progress, setProgress] = useState<{
    chunksIngested: number;
    currentFileChunks: number;
    totalFileChunks: number;
    filesProcessed: number;
    source: string;
  } | null>(null);

  const [files, setFiles] = useState<FileList | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [ingestDirectory, setIngestDirectory] = useState("");
  const dirInputRef = useRef<HTMLInputElement>(null);

  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);

  const [isProcessing, setIsProcessing] = useState(false);
  const [resultMessage, setResultMessage] = useState<string>("");

  const [ltmSize, setLtmSize] = useState(0);

  const [isExportingLTM, setIsExportingLTM] = useState(false);
  const [isImportingLTM, setIsImportingLTM] = useState(false);
  const ltmFileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    apiClient
      .get("/api/memory/qdrant/collections")
      .then((res) => {
        setCollections(res.data.collections || []);
        setSelectedCollection("");
      })
      .catch((err) => console.error("Failed to load collections:", err));
  }, []);

  useEffect(() => {
    const fetchLTMSize = async () => {
      try {
        const res = await apiClient.get("/api/memory/qdrant/status");
        setLtmSize(res.data.size || 0);
      } catch (err) {
        console.error("Failed to fetch LTM size:", err);
      }
    };

    fetchLTMSize();
    const interval = setInterval(fetchLTMSize, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "ingest_progress") {
          setProgress({
            chunksIngested: msg.chunks_ingested,
            currentFileChunks: msg.current_file_chunks,
            totalFileChunks: msg.total_file_chunks,
            filesProcessed: msg.files_processed,
            source: msg.source,
          });
        }
      } catch {}
    };

    ws.onclose = () => {};
    ws.onerror = () => {};

    return () => ws.close();
  }, []);

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) return;

    try {
      await apiClient.post("/api/memory/qdrant/collection", {
        name: newCollectionName.trim(),
        action: "create",
      });
      setCollections((prev) => [...prev, newCollectionName.trim()]);
      setSelectedCollection(newCollectionName.trim());
      setNewCollectionName("");
      setMode("select");
    } catch (err) {
      console.error("Failed to create collection:", err);
      setResultMessage(
        `✗ Failed to create collection: ${(err as any).response?.data?.detail || (err as Error).message}`
      );
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFiles(e.target.files);
    setResultMessage("");
  };

  const handleBrowseFilesClick = () => {
    fileInputRef.current?.click();
  };

  const handleDirectoryBrowse = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;

    try {
      const res = await apiClient.get("/api/system/workspace-path");
      const workspacePath = res.data.workspace_path;

      const firstFile = selectedFiles[0] as any;
      if (firstFile.webkitRelativePath) {
        const pathParts = firstFile.webkitRelativePath.split("/");
        if (pathParts.length > 1) {
          pathParts.pop();
          const relativePath = pathParts.join("/");
          setIngestDirectory(`${workspacePath}/${relativePath}`);
          setResultMessage("");
        }
      }
    } catch (err) {
      console.error("Failed to get workspace path:", err);
      const firstFile = selectedFiles[0] as any;
      if (firstFile.webkitRelativePath) {
        const pathParts = firstFile.webkitRelativePath.split("/");
        pathParts.pop();
        setIngestDirectory(pathParts.join("/"));
      }
    }
  };

  const handleBrowseDirClick = () => {
    dirInputRef.current?.click();
  };

  const hasSource = (files && files.length > 0) || ingestDirectory.trim().length > 0;
  const canProcess = !isProcessing && !!selectedCollection && hasSource;

  const handleChunkAndIngest = async () => {
    if (!selectedCollection || !hasSource) return;

    setIsProcessing(true);
    setResultMessage("");
    setProgress(null);

    try {
      let response;

      if (files && files.length > 0) {
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
          formData.append("files", files[i]);
        }
        formData.append("collection", selectedCollection);
        formData.append("chunk_size", String(chunkSize));
        formData.append("chunk_overlap", String(chunkOverlap));

        response = await apiClient.post("/api/memory/qdrant/chunk-and-ingest", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else {
        response = await apiClient.post("/api/memory/qdrant/chunk-and-ingest", null, {
          params: {
            collection: selectedCollection,
            directory: ingestDirectory.trim(),
            chunk_size: chunkSize,
            chunk_overlap: chunkOverlap,
          },
        });
      }

      const data = response.data;

      let msg: string;
      if (data.status === "duplicate") {
        msg = `⚠ All content already exists in ${selectedCollection} (${data.files_processed} files, ${data.duplicates_skipped} chunks skipped)`;
      } else if (data.status === "partial") {
        msg = `✓ ${data.total_chunks} new chunks ingested, ${data.duplicates_skipped} duplicates skipped from ${data.files_processed} files → ${selectedCollection}`;
      } else if (data.total_chunks > 0) {
        msg = `✓ ${data.total_chunks} chunks from ${data.files_processed} files → ${selectedCollection}`;
      } else {
        msg = "No supported files found";
      }

      setResultMessage(msg);

      setFiles(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setIngestDirectory("");
      setSelectedCollection("");
      setProgress(null);
    } catch (error: any) {
      setResultMessage(`✗ ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleExportLTM = async () => {
    setIsExportingLTM(true);
    try {
      const response = await apiClient.get("/api/memory/qdrant/collections");
      const cols = response.data.collections || [];

      const backup = {
        timestamp: new Date().toISOString(),
        version: "1.0.0",
        type: "qdrant",
        collections: cols.map((col: any) => ({
          name: col.name ?? col,
          points_count: col.points_count || 0,
          vectors_count: col.vectors_count || 0,
        })),
      };

      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `mai-rag-ltm-backup-${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("LTM export failed:", err);
      setResultMessage("✗ Failed to export LTM backup");
    } finally {
      setIsExportingLTM(false);
    }
  };

  const handleImportLTM = () => {
    ltmFileInputRef.current?.click();
  };

  const handleLTMFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!window.confirm("This will merge LTM backup data. Continue?")) return;

    setIsImportingLTM(true);
    try {
      await file.text();
      setResultMessage("⚠ LTM import not yet implemented");
    } catch (err) {
      console.error("LTM import failed:", err);
      setResultMessage("✗ Failed to import LTM backup");
    } finally {
      setIsImportingLTM(false);
      if (ltmFileInputRef.current) ltmFileInputRef.current.value = "";
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${Math.round((bytes / Math.pow(k, i)) * 100) / 100} ${sizes[i]}`;
  };

  return (
    <section
      className="console reveal delay-2 file-upload-panel glow-panel"
      role="region"
      aria-label="Long-Term Memory Manager"
      style={{
        minHeight: "auto",
        height: "auto",
        display: "flex",
        flexDirection: "column",
        padding: "16px 24px",
        boxSizing: "border-box",
        marginBottom: "24px",
      }}
    >
      <div
        className="console-title"
        style={{ color: "var(--accent)", fontSize: "1.3rem", fontWeight: "bold", marginBottom: "12px" }}
      >
        Long-Term Memory
      </div>

      <p style={{ fontSize: "0.9rem", opacity: 0.9, margin: "0 0 12px 0" }}>
        IMPORTANT: Upload documents to their own Individual Subject Centric Database.
        <br />
        ie: Biology, InteriorDesign, etc. This ensures faster search response time.
      </p>

      <div style={{ display: "flex", gap: "8px", marginBottom: "8px" }} role="group" aria-label="Collection mode selection">
        <button
          onClick={() => setMode("select")}
          role="tab"
          aria-selected={mode === "select"}
          aria-label="Use existing collection"
          style={{
            flex: 1,
            padding: "6px 10px",
            borderRadius: "6px",
            border: mode === "select" ? "1px solid var(--accent)" : "1px solid var(--line)",
            background: mode === "select" ? "rgba(124,246,211,0.1)" : "transparent",
            color: "var(--text)",
            cursor: "pointer",
            fontSize: "0.85rem",
          }}
        >
          Use Existing
        </button>
        <button
          onClick={() => setMode("create")}
          role="tab"
          aria-selected={mode === "create"}
          aria-label="Create new collection"
          style={{
            flex: 1,
            padding: "6px 10px",
            borderRadius: "6px",
            border: mode === "create" ? "1px solid var(--accent)" : "1px solid var(--line)",
            background: mode === "create" ? "rgba(124,246,211,0.1)" : "transparent",
            color: "var(--text)",
            cursor: "pointer",
            fontSize: "0.85rem",
          }}
        >
          Create New
        </button>
      </div>

      {mode === "select" ? (
        <div style={{ display: "flex", gap: "8px" }}>
          <select
            value={selectedCollection}
            onChange={(e) => setSelectedCollection(e.target.value)}
            aria-label="Select collection"
            style={{
              flex: 1,
              padding: "8px 10px",
              borderRadius: "6px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.04)",
              color: selectedCollection ? "var(--text)" : "#888",
              fontSize: "0.9rem",
            }}
          >
            <option value="" disabled>
              Select or Create New Database
            </option>
            {collections.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <button
            onClick={async () => {
              if (!selectedCollection) return;
              if (!window.confirm(`Delete collection "${selectedCollection}" and all its data? This cannot be undone.`)) return;
              try {
                await apiClient.post("/api/memory/qdrant/collection", {
                  name: selectedCollection,
                  action: "delete",
                });
                setCollections((prev) => prev.filter((c) => c !== selectedCollection));
                setSelectedCollection("");
                setResultMessage(`✓ Deleted collection: ${selectedCollection}`);
              } catch (err: any) {
                setResultMessage(`✗ Failed to delete: ${err.response?.data?.detail || err.message}`);
              }
            }}
            disabled={!selectedCollection}
            aria-label="Delete selected collection"
            title="Delete selected collection"
            style={{
              padding: "8px 12px",
              borderRadius: "6px",
              border: "1px solid #ef4444",
              background: "transparent",
              color: selectedCollection ? "#ef4444" : "#666",
              cursor: selectedCollection ? "pointer" : "not-allowed",
              fontSize: "0.85rem",
              fontWeight: 600,
              whiteSpace: "nowrap",
            }}
          >
            Delete
          </button>
        </div>
      ) : (
        <div style={{ display: "flex", gap: "8px" }}>
          <input
            type="text"
            value={newCollectionName}
            onChange={(e) => setNewCollectionName(e.target.value)}
            placeholder="Enter new collection name"
            aria-label="New collection name"
            style={{
              flex: 1,
              padding: "8px 10px",
              borderRadius: "6px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.04)",
              color: "var(--text)",
              fontSize: "0.9rem",
              boxSizing: "border-box",
            }}
          />
          <button
            onClick={handleCreateCollection}
            disabled={!newCollectionName.trim()}
            aria-label="Create collection"
            style={{
              padding: "8px 12px",
              borderRadius: "6px",
              border: "none",
              background: newCollectionName.trim() ? "var(--accent)" : "rgba(255,255,255,0.08)",
              color: newCollectionName.trim() ? "#000" : "#666",
              cursor: newCollectionName.trim() ? "pointer" : "not-allowed",
              fontSize: "0.85rem",
              fontWeight: 700,
              whiteSpace: "nowrap",
            }}
          >
            Create
          </button>
        </div>
      )}

      <div
        style={{
          paddingTop: "12px",
          borderTop: "1px solid var(--line)",
          marginTop: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
        role="group"
        aria-label="Source selection"
      >
        <label style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--accent)", marginBottom: "4px" }}>
          Source
        </label>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            onClick={handleBrowseFilesClick}
            aria-label="Upload single files"
            style={{
              flex: 1,
              padding: "8px 10px",
              borderRadius: "6px",
              background: files ? "rgba(124,246,211,0.15)" : "rgba(255,255,255,0.08)",
              color: files ? "var(--text)" : "#888",
              border: "1px solid var(--line)",
              cursor: "pointer",
              fontSize: "0.85rem",
              textAlign: "left",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {files
              ? `${files.length} file${files.length > 1 ? "s" : ""} selected`
              : "Upload Single Files Here (.pdf .epub .txt .md .pptx .py .js .json .yaml .yml .html .htm .xlsx .csv .tsv .jsonl .parquet .arrow .sqlite .db)"}
          </button>
          <input
            type="file"
            multiple
            ref={fileInputRef}
            onChange={handleFileChange}
            style={{ display: "none" }}
            aria-label="File input"
          />
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <input
            type="text"
            value={ingestDirectory}
            onChange={(e) => setIngestDirectory(e.target.value)}
            placeholder="Or upload an entire subject centric pre-organized directory"
            aria-label="Directory path"
            style={{
              flex: 1,
              padding: "8px 10px",
              borderRadius: "6px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.04)",
              color: ingestDirectory ? "var(--text)" : "#888",
              fontSize: "0.85rem",
              boxSizing: "border-box",
            }}
          />
          <button
            onClick={handleBrowseDirClick}
            aria-label="Browse directory"
            style={{
              padding: "8px 12px",
              borderRadius: "6px",
              background: "rgba(255,255,255,0.08)",
              color: "var(--text)",
              border: "1px solid var(--line)",
              cursor: "pointer",
              fontSize: "0.85rem",
              whiteSpace: "nowrap",
            }}
          >
            Browse
          </button>
          <input
            type="file"
            ref={dirInputRef}
            onChange={handleDirectoryBrowse}
            style={{ display: "none" }}
            {...({ webkitdirectory: "", directory: "", mozdirectory: "" } as any)}
            aria-label="Directory input"
          />
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", opacity: 0.7, display: "block", marginBottom: "2px" }}>
              Chunk Size
            </label>
            <input
              type="number"
              value={chunkSize}
              onChange={(e) => setChunkSize(Number(e.target.value))}
              min={100}
              max={10000}
              aria-label="Chunk size"
              style={{
                width: "100%",
                padding: "6px 8px",
                borderRadius: "6px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "var(--text)",
                fontSize: "0.85rem",
                boxSizing: "border-box",
              }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: "0.75rem", opacity: 0.7, display: "block", marginBottom: "2px" }}>
              Overlap
            </label>
            <input
              type="number"
              value={chunkOverlap}
              onChange={(e) => setChunkOverlap(Number(e.target.value))}
              min={0}
              max={1000}
              aria-label="Chunk overlap"
              style={{
                width: "100%",
                padding: "6px 8px",
                borderRadius: "6px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.04)",
                color: "var(--text)",
                fontSize: "0.85rem",
                boxSizing: "border-box",
              }}
            />
          </div>
        </div>
      </div>

      <div style={{ paddingTop: "12px", marginTop: "4px" }}>
        <button
          onClick={handleChunkAndIngest}
          disabled={!canProcess}
          aria-label="Chunk and ingest into database"
          style={{
            width: "100%",
            padding: "12px",
            borderRadius: "6px",
            background: !canProcess ? "rgba(255,255,255,0.08)" : "var(--accent)",
            color: !canProcess ? "#666" : "#000",
            border: "none",
            cursor: !canProcess ? "not-allowed" : "pointer",
            fontSize: "0.95rem",
            fontWeight: 700,
            transition: "background 0.2s",
          }}
        >
          {isProcessing ? "Processing…" : "Chunk & Ingest"}
        </button>
      </div>

      <div style={{ marginTop: "8px", minHeight: "36px" }}>
        {isProcessing && progress ? (
          <div>
            <div style={{ fontSize: "0.8rem", marginBottom: "4px", color: "var(--text)", opacity: 0.9 }}>
              Processing: {progress.source} ({progress.currentFileChunks}/{progress.totalFileChunks} chunks)
            </div>
            <div
              style={{
                position: "relative",
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.12)",
                background: "rgba(255,255,255,0.04)",
                height: "20px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  height: "100%",
                  width: `${Math.min(100, Math.round((progress.currentFileChunks / Math.max(1, progress.totalFileChunks)) * 100))}%`,
                  backgroundColor: "var(--accent)",
                  opacity: 0.5,
                  transition: "width 0.3s",
                }}
                role="progressbar"
                aria-valuenow={progress.currentFileChunks}
                aria-valuemax={progress.totalFileChunks}
              />
              <div
                style={{
                  position: "relative",
                  zIndex: 1,
                  textAlign: "center",
                  lineHeight: "20px",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                }}
              >
                {Math.round((progress.currentFileChunks / Math.max(1, progress.totalFileChunks)) * 100)}%
              </div>
            </div>
            <div style={{ fontSize: "0.75rem", opacity: 0.7, marginTop: "2px" }}>
              Total: {progress.chunksIngested} chunks from {progress.filesProcessed} files
            </div>
          </div>
        ) : resultMessage ? (
          <div
            style={{
              fontSize: "0.8rem",
              padding: "8px 10px",
              borderRadius: "4px",
              background: resultMessage.startsWith("✓") ? "rgba(124,246,211,0.1)" : "rgba(239,68,68,0.1)",
              border: `1px solid ${resultMessage.startsWith("✓") ? "var(--accent)" : "#ef4444"}`,
              color: resultMessage.startsWith("✓") ? "var(--accent)" : "#fca5a5",
            }}
            role="status"
            aria-live="polite"
          >
            {resultMessage}
          </div>
        ) : null}
      </div>

      <div
        style={{
          paddingTop: "12px",
          borderTop: "1px solid var(--line)",
          marginTop: "12px",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "12px",
        }}
      >
        <div role="stat" aria-label="LTM storage size">
          <div style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "8px", color: "var(--accent)" }}>
            Long-Term Memory Storage
          </div>
          <div style={{ padding: "10px", borderRadius: "6px", background: "rgba(255,255,255,0.04)", border: "1px solid var(--line)" }}>
            <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent)" }}>
              {formatSize(ltmSize)}
            </div>
          </div>
        </div>

        <div role="stat" aria-label="Number of collections">
          <div style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "8px", color: "var(--accent)" }}>
            Database Collections
          </div>
          <div style={{ padding: "10px", borderRadius: "6px", background: "rgba(255,255,255,0.04)", border: "1px solid var(--line)" }}>
            <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent)" }}>
              {collections.length}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: "12px" }} role="group" aria-label="LTM backup options">
        <div style={{ fontSize: "0.85rem", fontWeight: 600, marginBottom: "8px", color: "var(--accent)" }}>
          Long-Term Memory Backup
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={handleExportLTM}
            disabled={isExportingLTM}
            aria-label="Export LTM backup"
            style={{
              flex: 1,
              padding: "10px 12px",
              borderRadius: "6px",
              border: "none",
              background: isExportingLTM ? "rgba(255,255,255,0.1)" : "var(--accent)",
              color: isExportingLTM ? "#666" : "#000",
              cursor: isExportingLTM ? "not-allowed" : "pointer",
              fontSize: "0.9rem",
              fontWeight: 600,
            }}
          >
            {isExportingLTM ? "Exporting…" : "Export LTM"}
          </button>
          <button
            onClick={handleImportLTM}
            disabled={isImportingLTM}
            aria-label="Import LTM backup"
            style={{
              flex: 1,
              padding: "10px 12px",
              borderRadius: "6px",
              border: "1px solid var(--accent)",
              background: "transparent",
              color: isImportingLTM ? "#666" : "var(--accent)",
              cursor: isImportingLTM ? "not-allowed" : "pointer",
              fontSize: "0.9rem",
              fontWeight: 600,
            }}
          >
            {isImportingLTM ? "Importing…" : "Import LTM"}
          </button>
        </div>
      </div>

      <input
        type="file"
        ref={ltmFileInputRef}
        onChange={handleLTMFileSelect}
        accept=".json"
        style={{ display: "none" }}
        aria-label="LTM import file"
      />
    </section>
  );
};

export default LongTermMemoryApp;
