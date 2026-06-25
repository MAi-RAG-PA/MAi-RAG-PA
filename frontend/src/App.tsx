import React, { useState, useEffect } from "react";
import Header from "./components/layout/Header";
import HeroSectionApp from "./components/HeroSectionApp";
import ChatConsoleApp from "./components/chat/ChatConsoleApp";
import TextEditorApp from "./components/notes/TextEditorApp";
import LongTermMemoryApp from "./components/memory/LongTermMemoryApp";
import ShortTermMemoryApp from "./components/memory/ShortTermMemoryApp";
import CalendarPlannerApp from "./components/planner/CalendarPlannerApp";
import EventsPanelApp from "./components/planner/EventsPanelApp";
import TodoManagerApp from "./components/planner/TodoManagerApp";
import PromptAndHeartbeatApp from "./components/settings/PromptAndHeartbeatApp";
import ToastNotificationApp from "./components/ToastNotificationApp";
import { useEventNotifications } from './hooks/useEventNotifications';
import EnvironmentSetupModal from './components/settings/EnvironmentSetupModal';

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
    
    window.addEventListener('show-toast', handleToast as EventListener);
    return () => window.removeEventListener('show-toast', handleToast as EventListener);
  }, []);

  useEventNotifications(showToast);

  const saveNote = () => {
    showToast(`Note "${noteFilename}" saved`);
  };

  return (
    <>
      <Header />
      <main className="wrap" style={{ paddingTop: 0 }}>
        <EnvironmentSetupModal />
        {/* Hero Section */}
        <section id="home" className="reveal delay-2" style={{ paddingTop: 0 }}>
          <HeroSectionApp />
        </section>

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
            {/* Left Column: Long-Term Memory */}
            <div style={{ flex: "1 1 400px", minWidth: 0, width: "100%" }}>
              <LongTermMemoryApp />
            </div>
    
            {/* Right Column: Short-Term + Analytics stacked */}
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
            <div style={{ marginTop: '-8px', marginBottom: 12 }}>
              <div className="mono" style={{ fontWeight: "bold", fontSize: "0.9rem" }}>
                Configuration & Preferences
              </div>
              <h2 style={{ marginTop: 2, marginBottom: 6 }}>Assistant Settings</h2>
              <p style={{ marginTop: 0, marginBottom: 4, maxWidth: 600, lineHeight: 1.4 }}>
                Steer the AI model with specific instructions based on your preferences.
              </p>
            </div>

            <section className="panel reveal delay-3 glow-panel" style={{ marginTop: 0, paddingTop: '12px' }}>
              <PromptAndHeartbeatApp showToast={showToast} />
            </section>
          </div>
        </section>

      </main>

      {/* Toast Notifications */}
      {toastMessage && <ToastNotificationApp message={toastMessage} onClose={() => setToastMessage(null)} />}
    </>
  );
};

export default App;
