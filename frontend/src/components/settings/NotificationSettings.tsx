// frontend/src/components/settings/NotificationSettings.tsx
import React, { useState, useEffect } from "react";
import apiClient from "../../api/client";

interface NotificationInterval {
  label: string;
  minutes: number;
  enabled: boolean;
}

interface NotificationSettingsProps {
  showToast: (msg: string) => void;
}

const DEFAULT_INTERVALS: NotificationInterval[] = [
  { label: "24h", minutes: 1440, enabled: true },
  { label: "1h", minutes: 60, enabled: true },
  { label: "30m", minutes: 30, enabled: true },
  { label: "15m", minutes: 15, enabled: true },
  { label: "5m", minutes: 5, enabled: true },
  { label: "0m", minutes: 0, enabled: true },
];

const NotificationSettings: React.FC<NotificationSettingsProps> = ({ showToast }) => {
  const [intervals, setIntervals] = useState<NotificationInterval[]>(DEFAULT_INTERVALS);
  const [isLoading, setIsLoading] = useState(false);

  const loadSettings = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get("/api/settings/notifications");
      const loadedIntervals = response.data?.intervals;

      if (Array.isArray(loadedIntervals) && loadedIntervals.length > 0) {
        setIntervals(loadedIntervals);
      } else {
        setIntervals(DEFAULT_INTERVALS);
      }
    } catch (err) {
      console.error("Failed to load notification settings:", err);
      showToast("Failed to load notification settings");
      setIntervals(DEFAULT_INTERVALS);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadSettings();
  }, []);

  const toggleInterval = (index: number) => {
    setIntervals((prev) =>
      prev.map((item, i) => (i === index ? { ...item, enabled: !item.enabled } : item))
    );
  };

  const saveSettings = async () => {
    setIsLoading(true);
    try {
      await apiClient.post("/api/settings/notifications", { intervals });
      showToast("Notification settings saved");
    } catch (err) {
      console.error("Failed to save notification settings:", err);
      showToast("Failed to save settings");
    } finally {
      setIsLoading(false);
    }
  };

  const getLabel = (label: string) => {
    switch (label) {
      case "24h":
        return "1 Day Before";
      case "1h":
        return "1 Hour Before";
      case "30m":
        return "30 Minutes Before";
      case "15m":
        return "15 Minutes Before";
      case "5m":
        return "5 Minutes Before";
      case "0m":
        return "At Event Time";
      default:
        return label;
    }
  };

  const getDescription = (interval: NotificationInterval) => {
    if (interval.minutes === 0) return "Notify exactly when event starts";
    if (interval.minutes >= 60) return `Notify ${interval.minutes / 60} hour(s) before`;
    return `Notify ${interval.minutes} minutes before`;
  };

  return (
    <div
      role="region"
      aria-label="Notification Schedule Settings"
      style={{ padding: "16px", background: "rgba(255,255,255,0.04)", borderRadius: "12px" }}
    >
      <h3 style={{ marginBottom: "16px", color: "var(--accent)", fontSize: "1.1rem", fontWeight: 600 }}>
        Notification Schedule
      </h3>
      <p style={{ fontSize: "0.9rem", opacity: 0.8, marginBottom: "16px", lineHeight: 1.4 }}>
        Choose when you want to be notified before events and reminders:
      </p>

      <div
        role="group"
        aria-label="Notification timing options"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        {(intervals || []).map((interval, index) => (
          <label
            key={interval.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "12px",
              background: interval.enabled ? "rgba(124, 246, 211, 0.08)" : "rgba(255,255,255,0.04)",
              borderRadius: "8px",
              cursor: "pointer",
              border: interval.enabled ? "1px solid var(--accent)" : "1px solid var(--line)",
              transition: "all 0.2s ease",
            }}
          >
            <input
              type="checkbox"
              checked={interval.enabled}
              onChange={() => toggleInterval(index)}
              aria-label={`Enable notification for ${getLabel(interval.label)}`}
              style={{ width: "20px", height: "20px", cursor: "pointer", accentColor: "var(--accent)" }}
            />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, color: interval.enabled ? "var(--accent)" : "var(--text)" }}>
                {getLabel(interval.label)}
              </div>
              <div style={{ fontSize: "0.85rem", opacity: 0.7 }}>{getDescription(interval)}</div>
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={saveSettings}
        disabled={isLoading}
        className="btn"
        aria-label={isLoading ? "Saving notification settings" : "Save notification settings"}
        style={{
          padding: "10px 20px",
          borderRadius: "8px",
          background: isLoading ? "rgba(255,255,255,0.1)" : "var(--accent, #7cf6d3)",
          color: isLoading ? "#666" : "#000",
          border: "none",
          cursor: isLoading ? "not-allowed" : "pointer",
          fontWeight: 600,
          width: "100%",
        }}
      >
        {isLoading ? "Saving..." : "Save Notification Settings"}
      </button>
    </div>
  );
};

export default NotificationSettings;
