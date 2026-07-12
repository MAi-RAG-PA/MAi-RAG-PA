// frontend/src/components/settings/EnvironmentSetupModal.tsx
import React, { useState, useEffect, useRef } from "react";
import apiClient from "../../api/client";

interface ServiceStatus {
  available: boolean;
  url?: string;
  download_url?: string;
  error?: string;
}

interface EnvironmentStatus {
  ollama: ServiceStatus;
  qdrant: ServiceStatus;
  all_services_available: boolean;
}

const EnvironmentSetupModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<EnvironmentStatus | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);
  const retryButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const focusTimerRef = useRef<number | null>(null);

  useEffect(() => {
    void checkEnvironment();
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;

    focusTimerRef.current = window.setTimeout(() => {
      retryButtonRef.current?.focus();
    }, 100);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setIsOpen(false);
        previouslyFocused?.focus();
        return;
      }

      if (e.key === "Tab" && modalRef.current) {
        const focusableElements = modalRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (!firstElement || !lastElement) return;

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      if (focusTimerRef.current !== null) {
        window.clearTimeout(focusTimerRef.current);
        focusTimerRef.current = null;
      }
      previouslyFocused?.focus();
    };
  }, [isOpen]);

  const checkEnvironment = async () => {
    setIsChecking(true);
    try {
      const response = await apiClient.get("/api/system/environment");
      setStatus(response.data);
      if (!response.data.all_services_available) {
        setIsOpen(true);
      }
      return response.data as EnvironmentStatus;
    } catch (err) {
      console.error("Failed to check environment:", err);
      return null;
    } finally {
      setIsChecking(false);
    }
  };

  const handleRetry = async () => {
    const latestStatus = await checkEnvironment();
    if (latestStatus?.all_services_available) {
      setIsOpen(false);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  if (!isOpen || !status) return null;

  const headingId = "env-modal-heading";
  const descriptionId = "env-modal-description";

  return (
    <div
      role="presentation"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.8)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "20px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        aria-describedby={descriptionId}
        style={{
          background: "var(--bg-secondary, #1a1a1a)",
          borderRadius: "12px",
          padding: "32px",
          maxWidth: "600px",
          width: "100%",
          border: "1px solid var(--line, #333)",
          boxShadow: "0 20px 60px rgba(0, 0, 0, 0.5)",
          maxHeight: "90vh",
          overflowY: "auto",
          position: "relative",
        }}
      >
        <button
          ref={closeButtonRef}
          onClick={handleClose}
          aria-label="Close setup dialog"
          style={{
            position: "absolute",
            top: "16px",
            right: "16px",
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid var(--line, #333)",
            borderRadius: "6px",
            width: "36px",
            height: "36px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            color: "var(--text, #fff)",
            fontSize: "1.25rem",
          }}
        >
          <span aria-hidden="true">×</span>
        </button>

        <h2
          id={headingId}
          style={{
            color: "var(--accent, #7cf6d3)",
            fontSize: "1.5rem",
            marginBottom: "8px",
            marginTop: 0,
            paddingRight: "40px",
          }}
        >
          Setup Required
        </h2>

        <p
          id={descriptionId}
          style={{
            color: "var(--text, #fff)",
            marginBottom: "24px",
            lineHeight: 1.6,
          }}
        >
          MAi-RAG requires the following services to be running for full functionality:
        </p>

        <div
          role="list"
          aria-label="Required services status"
          style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "24px" }}
        >
          <div
            role="listitem"
            aria-label={`Ollama service ${status.ollama.available ? "available" : "not available"}`}
            style={{
              padding: "16px",
              borderRadius: "8px",
              background: status.ollama.available ? "rgba(124, 246, 211, 0.1)" : "rgba(239, 68, 68, 0.1)",
              border: `1px solid ${status.ollama.available ? "var(--accent, #7cf6d3)" : "#ef4444"}`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <strong style={{ color: "var(--text, #fff)", fontSize: "1.1rem" }}>
                <span aria-hidden="true">{status.ollama.available ? "✓" : "✗"}</span>
                {" "}Ollama
              </strong>
              {!status.ollama.available && (
                <a
                  href="https://github.com/ollama/ollama/releases"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Download Ollama from GitHub Releases (opens in new tab)"
                  style={{
                    padding: "6px 12px",
                    borderRadius: "6px",
                    background: "var(--accent, #7cf6d3)",
                    color: "#000",
                    textDecoration: "none",
                    fontSize: "0.85rem",
                    fontWeight: 600,
                  }}
                >
                  Download
                </a>
              )}
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary, #aaa)", lineHeight: 1.5 }}>
              {status.ollama.available ? (
                `Running at ${status.ollama.url}`
              ) : (
                <>
                  Required for AI model inference.<br />
                  Download from <strong>GitHub Releases</strong>, extract, and run the binary directly.<br />
                  Or use the install script:{" "}
                  <code style={{ background: "rgba(255,255,255,0.1)", padding: "2px 6px", borderRadius: "4px", fontSize: "0.8rem" }}>
                    curl -fsSL https://ollama.com/install.sh | sh
                  </code>
                </>
              )}
            </div>
          </div>

          <div
            role="listitem"
            aria-label={`Qdrant service ${status.qdrant.available ? "available" : "not available"}`}
            style={{
              padding: "16px",
              borderRadius: "8px",
              background: status.qdrant.available ? "rgba(124, 246, 211, 0.1)" : "rgba(239, 68, 68, 0.1)",
              border: `1px solid ${status.qdrant.available ? "var(--accent, #7cf6d3)" : "#ef4444"}`,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <strong style={{ color: "var(--text, #fff)", fontSize: "1.1rem" }}>
                <span aria-hidden="true">{status.qdrant.available ? "✓" : "✗"}</span>
                {" "}Qdrant
              </strong>
              {!status.qdrant.available && (
                <a
                  href="https://github.com/qdrant/qdrant/releases"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="Download Qdrant standalone binary from GitHub Releases (opens in new tab)"
                  style={{
                    padding: "6px 12px",
                    borderRadius: "6px",
                    background: "var(--accent, #7cf6d3)",
                    color: "#000",
                    textDecoration: "none",
                    fontSize: "0.85rem",
                    fontWeight: 600,
                  }}
                >
                  Download Binary
                </a>
              )}
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary, #aaa)", lineHeight: 1.5 }}>
              {status.qdrant.available ? (
                `Running at ${status.qdrant.url}`
              ) : (
                <>
                  Required for long-term memory (RAG).<br />
                  Download the <strong>standalone binary</strong> for your platform from GitHub Releases.<br />
                  Place it in your project root and make it executable:{" "}
                  <code style={{ background: "rgba(255,255,255,0.1)", padding: "2px 6px", borderRadius: "4px", fontSize: "0.8rem" }}>
                    chmod +x qdrant
                  </code>
                </>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px" }}>
          <button
            ref={retryButtonRef}
            onClick={() => void handleRetry()}
            disabled={isChecking}
            aria-busy={isChecking}
            aria-label={isChecking ? "Checking services, please wait" : "Retry service connection"}
            style={{
              flex: 1,
              padding: "12px",
              borderRadius: "8px",
              background: isChecking ? "rgba(255, 255, 255, 0.1)" : "var(--accent, #7cf6d3)",
              color: isChecking ? "#666" : "#000",
              border: "none",
              cursor: isChecking ? "not-allowed" : "pointer",
              fontWeight: 600,
              fontSize: "0.95rem",
            }}
          >
            {isChecking ? "Checking..." : "Retry Connection"}
          </button>
          <button
            onClick={handleClose}
            aria-label="Continue without required services (some features will be limited)"
            style={{
              flex: 1,
              padding: "12px",
              borderRadius: "8px",
              background: "transparent",
              color: "var(--text, #fff)",
              border: "1px solid var(--line, #333)",
              cursor: "pointer",
              fontWeight: 600,
              fontSize: "0.95rem",
            }}
          >
            Continue Anyway
          </button>
        </div>

        <p
          role="note"
          style={{
            fontSize: "0.8rem",
            color: "var(--text-secondary, #aaa)",
            marginTop: "16px",
            marginBottom: 0,
            textAlign: "center",
          }}
        >
          You can continue using MAi-RAG, but some features will be limited until services are running.
        </p>
      </div>
    </div>
  );
};

export default EnvironmentSetupModal;
