// frontend/src/components/settings/SystemPromptPanel.tsx
import React, { useState, useEffect, useRef } from "react";
import apiClient from "../../api/client";

interface SystemPromptPanelProps {
  showToast: (msg: string) => void;
}

interface ActiveRole {
  id: string;
  name: string;
  system_prompt: string;
  collection_name: string | null;
  citations_enabled: boolean;
  model_override: string | null;
}

type EditMode = "global" | "role";

const SystemPromptPanel: React.FC<SystemPromptPanelProps> = ({ showToast }) => {
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [activeRole, setActiveRole] = useState<ActiveRole | null>(null);
  const [editMode, setEditMode] = useState<EditMode>("global");
  const [rolePromptBackup, setRolePromptBackup] = useState<string>("");
  const [globalPromptBackup, setGlobalPromptBackup] = useState<string>("");
  const isSavingRef = useRef(false);

  // ---- Load active role + global prompt on mount ----
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      try {
        const [roleRes, promptRes] = await Promise.all([
          apiClient.get("/api/v1/roles/active").catch(() => ({ data: null })),
          apiClient.get("/api/settings/system-prompt").catch(() => ({ data: { prompt: "" } })),
        ]);

        const role: ActiveRole | null =
          roleRes.data && roleRes.data.id ? roleRes.data : null;
        const globalPrompt: string = promptRes.data?.prompt || "";

        setActiveRole(role);
        setGlobalPromptBackup(globalPrompt);

        if (role) {
          setEditMode("role");
          setPrompt(role.system_prompt);
          setRolePromptBackup(role.system_prompt);
        } else {
          setEditMode("global");
          setPrompt(globalPrompt);
        }
      } catch (error) {
        console.error("Failed to init SystemPromptPanel:", error);
        showToast("Could not load system prompt");
      } finally {
        setIsLoading(false);
      }
    };
    init();
  }, []);

  // ---- Toggle between role and global edit mode ----
  const switchMode = (newMode: EditMode) => {
    if (newMode === editMode) return;

    if (editMode === "role") {
      setRolePromptBackup(prompt);
    } else {
      setGlobalPromptBackup(prompt);
    }

    if (newMode === "role" && activeRole) {
      setPrompt(rolePromptBackup || activeRole.system_prompt);
    } else if (newMode === "global") {
      setPrompt(globalPromptBackup);
    }
    setEditMode(newMode);
  };

  // ---- Reload current mode's content from DB ----
  const reloadCurrent = async () => {
    setIsLoading(true);
    try {
      if (editMode === "role" && activeRole) {
        const res = await apiClient.get("/api/v1/roles/active");
        const role: ActiveRole | null =
          res.data && res.data.id ? res.data : null;
        if (role) {
          setActiveRole(role);
          setPrompt(role.system_prompt);
          setRolePromptBackup(role.system_prompt);
        }
      } else {
        const res = await apiClient.get("/api/settings/system-prompt");
        const globalPrompt: string = res.data?.prompt || "";
        setPrompt(globalPrompt);
        setGlobalPromptBackup(globalPrompt);
      }
    } catch (error) {
      console.error("Failed to reload prompt:", error);
      showToast("Could not reload prompt");
    } finally {
      setIsLoading(false);
    }
  };

  // ---- Load the server's default system prompt template ----
  const loadServerDefault = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get("/api/settings/system-prompt/default");
      if (response.data?.prompt !== undefined) {
        setPrompt(response.data.prompt);
        showToast("Default template loaded — click Save to apply");
      }
    } catch (error) {
      console.error("Failed to load default prompt:", error);
      showToast("Could not load default prompt");
    } finally {
      setIsLoading(false);
    }
  };

  // ---- Save ----
  const savePrompt = async () => {
    if (isSavingRef.current || isLoading) return;
    if (!prompt.trim()) {
      showToast("Prompt cannot be empty");
      return;
    }

    isSavingRef.current = true;
    setIsLoading(true);

    try {
      if (editMode === "role" && activeRole) {
        await apiClient.put(`/api/v1/roles/${activeRole.id}`, {
          name: activeRole.name,
          system_prompt: prompt.trim(),
          collection_name: activeRole.collection_name,
          citations_enabled: activeRole.citations_enabled,
          model_override: activeRole.model_override,
        });
        setRolePromptBackup(prompt.trim());
        setActiveRole({ ...activeRole, system_prompt: prompt.trim() });
        showToast(`Role "${activeRole.name}" prompt saved ✓`);
      } else {
        await apiClient.post("/api/settings/system-prompt", {
          filename: "system_prompt",
          content: prompt.trim(),
        });
        setGlobalPromptBackup(prompt.trim());
        showToast("Global system prompt saved ✓");
      }
      setLastSaved(new Date().toLocaleTimeString());
    } catch (error: any) {
      console.error("Failed to save prompt:", error);
      const errorMsg =
        error.response?.data?.detail || "Failed to save prompt";
      showToast(errorMsg);
    } finally {
      setIsLoading(false);
      isSavingRef.current = false;
    }
  };

  const modeLabel =
    editMode === "role" && activeRole
      ? `Role: ${activeRole.name}`
      : "Global (all roles)";

  const helpText =
    editMode === "role"
      ? `Editing the system prompt for role "${activeRole?.name}". This overrides the global prompt when this role is active.`
      : "Editing the global system prompt. Used when no role is active.";

  return (
    <section className="panel reveal delay-2 glow-panel" aria-label="System Prompt Settings">
      <div className="panel-inner" style={{ padding: "22px 22px 16px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 12,
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          <h3 className="console-title" style={{ margin: 0 }}>
            System Prompt
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: "0.75rem" }}>
            {activeRole && (
              <span
                style={{
                  padding: "3px 10px",
                  borderRadius: 10,
                  background:
                    editMode === "role"
                      ? "rgba(124,246,211,0.15)"
                      : "rgba(255,255,255,0.06)",
                  border:
                    "1px solid " +
                    (editMode === "role" ? "var(--accent)" : "var(--line)"),
                  color: editMode === "role" ? "var(--accent)" : "var(--text)",
                  fontWeight: 600,
                }}
              >
                {modeLabel}
              </span>
            )}
            {lastSaved && <span style={{ opacity: 0.6 }}>Saved: {lastSaved}</span>}
          </div>
        </div>

        {activeRole && (
          <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
            <button
              onClick={() => switchMode("role")}
              className="chip"
              style={{
                padding: "5px 14px",
                borderRadius: 8,
                border:
                  "1px solid " +
                  (editMode === "role" ? "var(--accent)" : "var(--line)"),
                background:
                  editMode === "role"
                    ? "rgba(124,246,211,0.12)"
                    : "rgba(255,255,255,0.04)",
                color: editMode === "role" ? "var(--accent)" : "var(--text)",
                cursor: "pointer",
                fontSize: "0.8rem",
                fontWeight: 500,
              }}
            >
              🎭 Role: {activeRole.name}
            </button>
            <button
              onClick={() => switchMode("global")}
              className="chip"
              style={{
                padding: "5px 14px",
                borderRadius: 8,
                border:
                  "1px solid " +
                  (editMode === "global" ? "var(--accent)" : "var(--line)"),
                background:
                  editMode === "global"
                    ? "rgba(124,246,211,0.12)"
                    : "rgba(255,255,255,0.04)",
                color: editMode === "global" ? "var(--accent)" : "var(--text)",
                cursor: "pointer",
                fontSize: "0.8rem",
                fontWeight: 500,
              }}
            >
              🌐 Global (all roles)
            </button>
          </div>
        )}

        <p style={{ fontSize: "0.9rem", opacity: 0.8, lineHeight: 1.4, margin: "0 0 16px 0" }}>
          {helpText}
        </p>

        <textarea
          id="systemPromptEditor"
          aria-label="System prompt text editor"
          placeholder="Enter your custom system prompt..."
          value={prompt}
          rows={15}
          onChange={(e) => setPrompt(e.target.value)}
          disabled={isLoading}
          style={{
            width: "100%",
            minHeight: 180,
            maxHeight: 300,
            padding: 12,
            borderRadius: 12,
            border: "1px solid var(--line)",
            background: "rgba(255,255,255,0.04)",
            color: "var(--text)",
            fontSize: "0.95rem",
            fontFamily: "monospace",
            resize: "vertical",
            outline: "none",
            marginBottom: 16,
          }}
        />

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            onClick={savePrompt}
            disabled={isLoading || !prompt.trim()}
            className="btn"
            style={{
              padding: "10px 20px",
              borderRadius: 12,
              backgroundColor: isLoading
                ? "rgba(255,255,255,0.1)"
                : "var(--accent, #7cf6d3)",
              color: isLoading ? "#666" : "#000",
              border: "none",
              cursor: isLoading ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            {isLoading
              ? "Saving..."
              : editMode === "role"
              ? "Save Role Prompt"
              : "Save Global Prompt"}
          </button>

          <button
            onClick={reloadCurrent}
            disabled={isLoading}
            className="chip"
            style={{
              padding: "10px 20px",
              borderRadius: 12,
              backgroundColor: "rgba(255,255,255,0.08)",
              color: "var(--text)",
              border: "1px solid var(--line)",
              cursor: isLoading ? "not-allowed" : "pointer",
            }}
          >
            Reload from Database
          </button>

          <button
            onClick={loadServerDefault}
            disabled={isLoading}
            className="chip"
            style={{
              padding: "10px 20px",
              borderRadius: 12,
              backgroundColor: "rgba(255,255,255,0.08)",
              color: "var(--text)",
              border: "1px solid var(--line)",
              cursor: isLoading ? "not-allowed" : "pointer",
              marginLeft: "auto",
            }}
          >
            Load Default Template
          </button>
        </div>

        <div style={{ marginTop: 16, fontSize: "0.75rem", opacity: 0.6, lineHeight: 1.4 }}>
          <strong>Tip:</strong>{" "}
          {activeRole
            ? `Role prompts override the global prompt when "${activeRole.name}" is active. Changes take effect on the next message.`
            : `Use clear, concise instructions. Always click "Save" to apply changes.`}
        </div>
      </div>
    </section>
  );
};

export default SystemPromptPanel;
