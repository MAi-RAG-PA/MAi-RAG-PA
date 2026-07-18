// frontend/src/components/settings/PromptAndHeartbeatApp.tsx
import React, { useState, useEffect } from "react";
import SystemPromptPanel from "./SystemPromptPanel";
import HeartbeatPanel from "./HeartbeatPanel";
import NotificationSettings from "./NotificationSettings";
import apiClient from "../../api/client";

interface PromptAndHeartbeatAppProps {
  showToast: (msg: string) => void;
}

interface DoctorReport {
  timestamp: string;
  checks: Array<{
    name: string;
    status: "pass" | "fail" | "warn";
    details: string;
  }>;
  fixes_applied: string[];
  warnings: string[];
  errors: string[];
  summary: {
    total_checks: number;
    passed: number;
    failed: number;
    health_score: number;
  };
  report_file?: string;
}

const getIsMobile = () => window.innerWidth <= 768;

const PromptAndHeartbeatApp: React.FC<PromptAndHeartbeatAppProps> = ({ showToast }) => {
  const [isMobile, setIsMobile] = useState<boolean>(getIsMobile);
  const [isRunningDoctor, setIsRunningDoctor] = useState(false);
  const [doctorReport, setDoctorReport] = useState<DoctorReport | null>(null);
  const [showDoctorModal, setShowDoctorModal] = useState(false);

  useEffect(() => {
    const handleResize = () => setIsMobile(getIsMobile());
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const runSystemDoctor = async () => {
    setIsRunningDoctor(true);
    setDoctorReport(null);
    setShowDoctorModal(true);

    try {
      const response = await apiClient.post("/api/system/doctor");
      setDoctorReport(response.data);

      if (response.data.summary.health_score >= 80) {
        showToast("System health check passed");
      } else if (response.data.summary.health_score >= 60) {
        showToast("System has some warnings");
      } else {
        showToast("System has critical issues");
      }
    } catch (err) {
      console.error("System doctor failed:", err);
      showToast("System doctor failed");
    } finally {
      setIsRunningDoctor(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pass":
        return "✅";
      case "fail":
        return "❌";
      case "warn":
        return "⚠️";
      default:
        return "❓";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pass":
        return "#10b981";
      case "fail":
        return "#ef4444";
      case "warn":
        return "#f59e0b";
      default:
        return "#6b7280";
    }
  };

  return (
    <section className="wrap" role="region" aria-label="Assistant Settings Configuration">
      <div
        className="section-head reveal"
        style={{
          marginBottom: isMobile ? 16 : 24,
          paddingTop: 8,
          paddingBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexDirection: isMobile ? "column" : "row",
          gap: isMobile ? 12 : 0,
        }}
      >
        <div style={{ flex: 1 }}>
          <h2
            className="console-title"
            style={{
              marginTop: 4,
              marginBottom: 8,
              color: "var(--accent, #7cf6d3)",
              fontSize: isMobile ? "1.1rem" : "1.25rem",
            }}
          >
            Assistant Settings Configuration
          </h2>
          <p
            style={{
              marginBottom: 4,
              maxWidth: 600,
              lineHeight: 1.4,
              color: "var(--text)",
              opacity: 0.9,
              fontSize: isMobile ? "0.85rem" : "1rem",
            }}
          >
            Customize behavior, maintenance cycles, and operating parameters.
          </p>
        </div>

        <button
          onClick={runSystemDoctor}
          disabled={isRunningDoctor}
          aria-label="Run comprehensive system diagnostics"
          title="Run comprehensive system diagnostics"
          style={{
            padding: isMobile ? "8px 14px" : "10px 20px",
            borderRadius: "8px",
            border: "1px solid var(--accent)",
            background: isRunningDoctor ? "rgba(255,255,255,0.05)" : "rgba(124, 246, 211, 0.1)",
            color: isRunningDoctor ? "var(--muted)" : "var(--accent)",
            cursor: isRunningDoctor ? "not-allowed" : "pointer",
            fontSize: isMobile ? "0.8rem" : "0.9rem",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s",
            whiteSpace: "nowrap",
            width: isMobile ? "100%" : "auto",
            justifyContent: "center",
          }}
        >
          {isRunningDoctor ? (
            <>
              <span style={{ animation: "spin 1s linear infinite" }} aria-hidden="true">
                ⚙️
              </span>
              Running...
            </>
          ) : (
            <>System Doctor</>
          )}
        </button>
      </div>

      <section
        className="panel reveal delay-2 glow-panel"
        style={{ marginBottom: isMobile ? "16px" : "24px" }}
        role="region"
        aria-label="Notification Settings"
      >
        <div className="panel-inner" style={{ padding: isMobile ? "14px" : "22px" }}>
          <NotificationSettings showToast={showToast} />
        </div>
      </section>

      <div
        className="grid"
        style={{
          display: "grid",
          gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
          gap: isMobile ? 16 : 24,
          paddingBottom: "16px",
        }}
      >
        <SystemPromptPanel showToast={showToast} />
        <HeartbeatPanel showToast={showToast} />
      </div>

      {showDoctorModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="system-health-report-title"
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: isMobile ? "10px" : "20px",
          }}
        >
          <div
            style={{
              background: "var(--panel-strong)",
              borderRadius: "16px",
              padding: isMobile ? "20px" : "32px",
              maxWidth: "700px",
              width: "100%",
              maxHeight: isMobile ? "90vh" : "80vh",
              overflowY: "auto",
              border: "2px solid var(--accent)",
              boxShadow: "0 0 40px rgba(124, 246, 211, 0.3)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
              <h2 id="system-health-report-title" style={{ margin: 0, color: "var(--accent)", fontSize: isMobile ? "1.2rem" : "1.5rem" }}>
                System Health Report
              </h2>
              <button
                onClick={() => setShowDoctorModal(false)}
                aria-label="Close health report"
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text)",
                  fontSize: "1.5rem",
                  cursor: "pointer",
                  padding: "0",
                  width: "32px",
                  height: "32px",
                }}
              >
                ×
              </button>
            </div>

            {isRunningDoctor ? (
              <div style={{ textAlign: "center", padding: "40px" }}>
                <div style={{ fontSize: "3rem", marginBottom: "16px", animation: "spin 2s linear infinite" }} aria-hidden="true">
                  ⚙️
                </div>
                <p style={{ color: "var(--text)", fontSize: "1.1rem", margin: 0 }} role="status" aria-live="polite">
                  Running system diagnostics...
                </p>
              </div>
            ) : doctorReport ? (
              <>
                <div
                  style={{
                    background: "rgba(255,255,255,0.05)",
                    borderRadius: "12px",
                    padding: isMobile ? "16px" : "20px",
                    marginBottom: "24px",
                    textAlign: "center",
                  }}
                  role="status"
                  aria-live="polite"
                >
                  <div
                    style={{
                      fontSize: isMobile ? "2.5rem" : "3rem",
                      fontWeight: "bold",
                      color:
                        doctorReport.summary.health_score >= 80
                          ? "#10b981"
                          : doctorReport.summary.health_score >= 60
                            ? "#f59e0b"
                            : "#ef4444",
                      marginBottom: "8px",
                    }}
                  >
                    {doctorReport.summary.health_score}%
                  </div>
                  <div style={{ color: "var(--muted)", fontSize: isMobile ? "0.8rem" : "0.9rem" }}>
                    System Health Score ({doctorReport.summary.passed}/{doctorReport.summary.total_checks} checks passed)
                  </div>
                </div>

                <div style={{ marginBottom: "24px" }}>
                  <h3 style={{ color: "var(--accent)", marginBottom: "12px", fontSize: isMobile ? "1rem" : "1.1rem" }}>
                    Diagnostic Checks
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }} role="list" aria-label="List of diagnostic checks">
                    {doctorReport.checks.map((check, idx) => (
                      <div
                        key={`${check.name}-${idx}`}
                        role="listitem"
                        style={{
                          padding: isMobile ? "10px" : "12px",
                          borderRadius: "8px",
                          background: "rgba(255,255,255,0.03)",
                          border: `1px solid ${getStatusColor(check.status)}30`,
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          gap: "8px",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "12px", flex: 1, minWidth: 0 }}>
                          <span style={{ fontSize: "1.2rem", flexShrink: 0 }} aria-hidden="true">
                            {getStatusIcon(check.status)}
                          </span>
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <div style={{ color: "var(--text)", fontWeight: 600, fontSize: isMobile ? "0.85rem" : "0.95rem" }}>
                              {check.name}
                            </div>
                            <div style={{ color: "var(--muted)", fontSize: isMobile ? "0.75rem" : "0.85rem", wordBreak: "break-word" }}>
                              {check.details}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {doctorReport.errors.length > 0 && (
                  <div style={{ marginBottom: "24px" }}>
                    <h3 style={{ color: "#ef4444", marginBottom: "12px", fontSize: isMobile ? "1rem" : "1.1rem" }}>
                      ❌ Critical Issues
                    </h3>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }} role="list" aria-label="List of errors">
                      {doctorReport.errors.map((error, idx) => (
                        <div
                          key={`${error}-${idx}`}
                          role="listitem"
                          style={{
                            padding: isMobile ? "10px" : "12px",
                            borderRadius: "8px",
                            background: "rgba(239, 68, 68, 0.1)",
                            border: "1px solid rgba(239, 68, 68, 0.3)",
                            color: "#fca5a5",
                            fontSize: isMobile ? "0.8rem" : "0.9rem",
                            wordBreak: "break-word",
                          }}
                        >
                          {error}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {doctorReport.warnings.length > 0 && (
                  <div style={{ marginBottom: "24px" }}>
                    <h3 style={{ color: "#f59e0b", marginBottom: "12px", fontSize: isMobile ? "1rem" : "1.1rem" }}>
                      Warnings
                    </h3>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }} role="list" aria-label="List of warnings">
                      {doctorReport.warnings.map((warning, idx) => (
                        <div
                          key={`${warning}-${idx}`}
                          role="listitem"
                          style={{
                            padding: isMobile ? "10px" : "12px",
                            borderRadius: "8px",
                            background: "rgba(245, 158, 11, 0.1)",
                            border: "1px solid rgba(245, 158, 11, 0.3)",
                            color: "#fcd34d",
                            fontSize: isMobile ? "0.8rem" : "0.9rem",
                            wordBreak: "break-word",
                          }}
                        >
                          {warning}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {doctorReport.report_file && (
                  <div
                    style={{
                      padding: "12px",
                      borderRadius: "8px",
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid var(--line)",
                      fontSize: isMobile ? "0.75rem" : "0.85rem",
                      color: "var(--muted)",
                      wordBreak: "break-all",
                    }}
                  >
                    Full report saved to: <code style={{ color: "var(--accent)" }}>{doctorReport.report_file}</code>
                  </div>
                )}
              </>
            ) : null}
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </section>
  );
};

export default PromptAndHeartbeatApp;
