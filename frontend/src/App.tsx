// frontend/src/App.tsx
import React, { useState, useEffect, lazy, Suspense } from "react";
import Header from "./components/layout/Header";
import HeroSectionApp from "./components/HeroSectionApp";
import ToastNotificationApp from './components/ToastNotificationApp';
import ErrorBoundary from "./components/ErrorBoundary";
import { useEventNotifications } from "./hooks/useEventNotifications";
import EnvironmentSetupModal from "./components/settings/EnvironmentSetupModal";
import { wsClient } from "./api/websocket";
import apiClient from "./api/client";

// Lazy load heavy components for code splitting
const ChatConsoleApp = lazy(() => import("./components/chat/ChatConsoleApp"));
const TextEditorApp = lazy(() => import("./components/notes/TextEditorApp"));
const LongTermMemoryApp = lazy(() => import("./components/memory/LongTermMemoryApp"));
const ShortTermMemoryApp = lazy(() => import("./components/memory/ShortTermMemoryApp"));
const CalendarPlannerApp = lazy(() => import("./components/planner/CalendarPlannerApp"));
const EventsPanelApp = lazy(() => import("./components/planner/EventsPanelApp"));
const TodoManagerApp = lazy(() => import("./components/planner/TodoManagerApp"));
const PromptAndHeartbeatApp = lazy(() => import("./components/settings/PromptAndHeartbeatApp"));

// Loading fallback component
const LoadingSpinner = () => (
  <div
    style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      padding: "2rem",
      minHeight: "200px",
    }}
  >
    <div
      style={{
        width: "40px",
        height: "40px",
        border: "4px solid var(--accent)",
        borderTop: "4px solid transparent",
        borderRadius: "50%",
        animation: "spin 1s linear infinite",
      }}
    />
    <style>{`
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `}</style>
  </div>
);

const App: React.FC = () => {
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [notesContent, setNotesContent] = useState("");
  const [noteFilename, setNoteFilename] = useState("");

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  useEffect(() => {
    const handleToast = (e: CustomEvent) => {
      showToast(e.detail.message);
    };

    window.addEventListener("show-toast", handleToast as EventListener);
    return () => window.removeEventListener("show-toast", handleToast as EventListener);
  }, []);

  useEffect(() => {
    wsClient.connect();
    return () => wsClient.disconnect();
  }, []);

  useEffect(() => {
    const unsub = wsClient.on("heartbeat", (data) => {
      console.log("Heartbeat:", data.status, data.message);
    });
    return unsub;
  }, []);

  useEffect(() => {
    const unsub = wsClient.on("notification", (data) => {
      showToast(`${data.title}: ${data.message}`);

      if (data.audio) {
        const audio = new Audio("/sounds/notification.mp3");
        audio.volume = 0.7;
        audio.play().catch(() => {});
      }
    });

    return unsub;
  }, [showToast]);

  useEventNotifications(showToast);

  const saveNote = () => {
    showToast(`Note "${noteFilename}" saved`);
  };

  useEffect(() => {
    const checkAlerts = async () => {
      try {
        const res = await apiClient.get("/api/memory/sqlite/reminders/check-alerts");
        const dueReminders = res.data.due_reminders || [];

        if (dueReminders.length > 0) {
          dueReminders.forEach((reminder: any) => {
            showToast(`${reminder.text}`);

            if (reminder.alert_type === "sound" || reminder.alert_type === "both") {
              const audio = new Audio(`/sounds/${reminder.alert_sound || "notification.mp3"}`);
              audio.volume = 0.7;
              audio.play().catch((err: any) => console.warn("Audio play failed:", err));
            }
          });
        }
      } catch (err) {
        console.error("Failed to check alerts:", err);
      }
    };

    const interval = setInterval(checkAlerts, 30000);
    checkAlerts();

    return () => clearInterval(interval);
  }, [showToast]);

  return (
    <ErrorBoundary>
      <Header />
      <main className="wrap" style={{ paddingTop: 0 }}>
        <EnvironmentSetupModal />

        {/* Hero Section - Not lazy loaded (above fold) */}
        <section id="home" className="reveal delay-2" style={{ paddingTop: 0 }}>
          <HeroSectionApp />
        </section>

        {/* Lazy loaded sections with Suspense */}
        <Suspense fallback={<LoadingSpinner />}>
          {/* Chat Console Section */}
          <section id="console" className="reveal delay-3" style={{ marginBottom: 32, paddingTop: 0 }}>
            <ChatConsoleApp showToast={showToast} />
          </section>

          {/* Text Editor / Notes Section */}
          <section id="notes" className="reveal delay-3" style={{ marginBottom: 48, paddingTop: 0 }}>
            <TextEditorApp
              content={notesContent}
              onContentChange={setNotesContent}
              filename={noteFilename}
              onFilenameChange={setNoteFilename}
              onSave={saveNote}
            />
          </section>

          {/* Memory Panels */}
          <section id="memory" className="reveal delay-3" style={{ marginBottom: 48, paddingTop: 0 }}>
            <div
              className="memory-upload-container"
              style={{
                display: "flex",
                gap: window.innerWidth <= 768 ? 16 : 24,
                alignItems: "flex-start",
                flexWrap: "wrap",
                flexDirection: window.innerWidth <= 768 ? "column" : "row",
              }}
            >
              <div style={{ flex: "1 1 400px", minWidth: 0, width: "100%" }}>
                <LongTermMemoryApp />
              </div>
              <div style={{ flex: "1 1 400px", minWidth: 0, width: "100%" }}>
                <ShortTermMemoryApp />
              </div>
            </div>
          </section>

          {/* Planner Section */}
          <section className="dashboard" id="planner" style={{ marginBottom: 48, paddingTop: 0 }}>
            <div className="wrap">
              <div className="section-head reveal delay-2" style={{ marginBottom: 24 }}>
                <div>
                  <div className="mono" style={{ fontWeight: "bold", fontSize: "0.9rem" }}>
                    Time Management Operations
                  </div>
                  <h2 style={{ marginTop: 4, marginBottom: 8 }}>Calendar, Scheduling, Events, Planner</h2>
                  <p style={{ marginBottom: 4, maxWidth: 600, lineHeight: 1.4 }}>
                    Designed as a practical interactive cockpit, not a generic dashboard.
                  </p>
                </div>
                <div className="mono" style={{ fontWeight: "bold", fontSize: "0.8rem", opacity: 0.7 }}>
                  Notifications and Alerts for your schedules and appointments
                </div>
              </div>

              <section
                className="panel reveal delay-2 glow-panel"
                aria-label="Calendar panel"
                style={{ marginBottom: 24 }}
              >
                <CalendarPlannerApp />
              </section>

              <div
                className="grid reveal delay-2"
                style={{
                  display: "grid",
                  gridTemplateColumns: window.innerWidth <= 768 ? "1fr" : "1fr 1fr",
                  gap: 24,
                }}
              >
                <EventsPanelApp />
                <TodoManagerApp />
              </div>
            </div>
          </section>

          {/* Assistant Settings Section */}
          <section id="settings" className="reveal delay-2" style={{ marginTop: 0, marginBottom: 32, paddingTop: 0 }}>
            <div className="wrap" style={{ paddingTop: 0, marginTop: 0 }}>
              <div style={{ marginTop: "-8px", marginBottom: 12 }}>
                <div className="mono" style={{ fontWeight: "bold", fontSize: "0.9rem" }}>
                  Configuration & Preferences
                </div>
                <h2 style={{ marginTop: 2, marginBottom: 6 }}>Assistant Settings</h2>
                <p style={{ marginTop: 0, marginBottom: 4, maxWidth: 600, lineHeight: 1.4 }}>
                  Steer the AI model with specific instructions based on your preferences.
                </p>
              </div>

              <section className="panel reveal delay-3 glow-panel" style={{ marginTop: 0, paddingTop: "12px" }}>
                <PromptAndHeartbeatApp showToast={showToast} />
              </section>
            </div>
          </section>
        </Suspense>
      </main>

      {/* Toast Notifications */}
      {toastMessage && <ToastNotificationApp message={toastMessage} onClose={() => setToastMessage(null)} />}
    </ErrorBoundary>
  );
};

export default App;
