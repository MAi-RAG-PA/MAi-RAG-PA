// frontend/src/components/settings/SystemPromptPanel.tsx
import React, { useState, useEffect, useRef } from "react";
import apiClient from "../../api/client";

interface SystemPromptPanelProps {
  showToast: (msg: string) => void;
}

const SystemPromptPanel: React.FC<SystemPromptPanelProps> = ({ showToast }) => {
  const [prompt, setPrompt] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const isSavingRef = useRef(false);

  const loadPrompt = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get("/api/settings/system-prompt");
      if (response.data?.prompt !== undefined) {
        setPrompt(response.data.prompt);
      }
    } catch (error) {
      console.error("Failed to load system prompt:", error);
      showToast("Could not load system prompt");
    } finally {
      setIsLoading(false);
    }
  };

  const loadDefaultPrompt = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get("/api/settings/system-prompt/default");
      if (response.data?.prompt !== undefined) {
        setPrompt(response.data.prompt);
        showToast("Default prompt loaded from server");
      }
    } catch (error) {
      console.error("Failed to load default prompt:", error);
      showToast("Could not load default prompt");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPrompt();
  }, []);

  const savePrompt = async () => {
    if (isSavingRef.current || isLoading) return;
    if (!prompt.trim()) {
      showToast("Prompt cannot be empty");
      return;
    }

    isSavingRef.current = true;
    setIsLoading(true);

    try {
      await apiClient.post("/api/settings/system-prompt", {
        filename: "system_prompt",
        content: prompt.trim(),
      });
      setLastSaved(new Date().toLocaleTimeString());
      showToast("System prompt saved ✓");
    } catch (error: any) {
      console.error("Failed to save system prompt:", error);
      const errorMsg = error.response?.data?.detail || "Failed to save system prompt";
      showToast(errorMsg);
    } finally {
      setIsLoading(false);
      isSavingRef.current = false;
    }
  };

  const resetToDefault = () => {
    setPrompt(DEFAULT_SYSTEM_PROMPT);
    showToast("Ultimate default prompt loaded");
  };

  return (
    <section className="panel reveal delay-2 glow-panel" aria-label="System Prompt Settings">
      <div className="panel-inner" style={{ padding: "22px 22px 16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 className="console-title" style={{ margin: 0 }}>
            System Prompt
          </h3>
          {lastSaved && <span style={{ fontSize: "0.75rem", opacity: 0.6 }}>Saved: {lastSaved}</span>}
        </div>

        <p style={{ fontSize: "0.9rem", opacity: 0.8, lineHeight: 1.4, margin: "0 0 16px 0" }}>
          Shape the assistant&apos;s behavior, memory tone, and baseline operating rules. Changes take effect on next request.
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
              backgroundColor: isLoading ? "rgba(255,255,255,0.1)" : "var(--accent, #7cf6d3)",
              color: isLoading ? "#666" : "#000",
              border: "none",
              cursor: isLoading ? "not-allowed" : "pointer",
              fontWeight: 600,
            }}
          >
            {isLoading ? "Saving..." : "Save Prompt"}
          </button>

          <button
            onClick={loadPrompt}
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
            onClick={resetToDefault}
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
            Reset to Default
          </button>
        </div>

        <div style={{ marginTop: 16, fontSize: "0.75rem", opacity: 0.6, lineHeight: 1.4 }}>
          <strong>Tip:</strong> Use clear, concise instructions. Avoid contradictory rules. Test changes with a simple query like
          &quot;What can you do? You can also Revert to default System Prompt. Always "SAVE PROMPT" to Apply changes. &quot;
        </div>
      </div>
    </section>
  );
};

export default SystemPromptPanel;
