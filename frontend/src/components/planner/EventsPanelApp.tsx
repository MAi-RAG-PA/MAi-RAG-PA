// frontend/src/components/planner/EventsPanelApp.tsx
import React, { useState, useEffect, useCallback } from "react";
import apiClient from "../../api/client";

interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start_time: string;
  end_time?: string;
  location?: string;
  category?: string;
  type?: "event" | "reminder";
}

const EventsPanelApp: React.FC = () => {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  const fetchEvents = useCallback(async () => {
    setIsLoading(true);

    try {
      const eventsRes = await apiClient.get("/api/memory/sqlite/events/upcoming?limit=20");
      const eventsList: CalendarEvent[] = (eventsRes.data?.events || []).map((e: any) => ({
        ...e,
        type: "event",
      }));

      const remindersRes = await apiClient.get("/api/memory/sqlite/reminders/upcoming?limit=20");
      const remindersList: CalendarEvent[] = (remindersRes.data?.reminders || []).map((r: any) => ({
        id: r.id,
        title: r.text,
        start_time: r.due_time,
        end_time: r.due_time,
        location: r.location,
        category: r.category,
        type: "reminder",
      }));

      const allItems = [...eventsList, ...remindersList];
      const now = new Date();

      const activeEvents = allItems
        .filter((item) => {
          const startTime = new Date(item.start_time);
          const endTime = item.end_time ? new Date(item.end_time) : null;
          return startTime >= now || (endTime !== null && endTime >= now);
        })
        .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

      setEvents(activeEvents);
      setLastUpdated(new Date());
    } catch (err) {
      console.warn("Failed to fetch events:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchEvents();

    const interval = setInterval(() => {
      void fetchEvents();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchEvents]);

  const formatDateTime = (iso: string) => {
    const date = new Date(iso);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    const isTomorrow = date.toDateString() === new Date(now.getTime() + 86400000).toDateString();

    const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    if (isToday) return `Today ${time}`;
    if (isTomorrow) return `Tomorrow ${time}`;

    return `${date.toLocaleDateString([], { month: "short", day: "numeric" })} ${time}`;
  };

  const getTimeUntil = (iso: string) => {
    const eventTime = new Date(iso);
    const diffMs = eventTime.getTime() - currentTime.getTime();

    if (diffMs < 0) return "Now";

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Now";
    if (diffMins < 60) return `in ${diffMins}m`;
    if (diffHours < 24) return `in ${diffHours}h ${diffMins % 60}m`;
    return `in ${diffDays}d ${diffHours % 24}h`;
  };

  return (
    <section
      className="panel reveal delay-1 glow-panel"
      role="region"
      aria-label="Upcoming events panel"
      style={{
        flex: "1 1 45%",
        minWidth: 300,
        maxHeight: "425px",
        display: "flex",
        flexDirection: "column",
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      <div
        className="panel-inner"
        style={{
          padding: 22,
          display: "flex",
          flexDirection: "column",
          height: "100%",
          overflow: "hidden",
        }}
      >
        <div style={{ marginBottom: 16, flexShrink: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <div
              className="console-title"
              style={{
                color: "var(--accent)",
                fontSize: "1.3rem",
                fontWeight: "bold",
              }}
            >
              Upcoming Events
            </div>
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              {lastUpdated && (
                <div style={{ fontSize: "0.75rem", opacity: 0.6 }} role="status" aria-live="polite">
                  Updated: {lastUpdated.toLocaleTimeString()}
                </div>
              )}
              <button
                onClick={() => void fetchEvents()}
                aria-label="Refresh events list"
                title="Refresh events"
                style={{
                  padding: "4px 8px",
                  borderRadius: "4px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.04)",
                  color: "var(--text)",
                  cursor: "pointer",
                  fontSize: "0.75rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                ↻
              </button>
            </div>
          </div>
          <div style={{ fontSize: "0.85rem", opacity: 0.7 }} role="status" aria-live="polite">
            {events.length} item{events.length !== 1 ? "s" : ""} scheduled
          </div>
        </div>

        <div
          className="timeline"
          role="list"
          aria-label="List of upcoming events and reminders"
          style={{
            flex: 1,
            overflowY: "auto",
            overflowX: "hidden",
            paddingRight: 12,
            display: "flex",
            flexDirection: "column",
            alignItems: "stretch",
            alignContent: "flex-start",
            minHeight: 0,
          }}
        >
          {isLoading ? (
            <div style={{ textAlign: "center", padding: "40px 0", opacity: 0.6 }} role="status" aria-live="polite">
              Loading events...
            </div>
          ) : events.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0", opacity: 0.6 }} role="status" aria-live="polite">
              <div>No upcoming events</div>
              <div style={{ fontSize: "0.85rem", marginTop: 8 }}>Create events in the Calendar Above</div>
            </div>
          ) : (
            (events || []).map((event, index) => (
              <article
                key={event.id}
                role="listitem"
                aria-label={`${event.title}${event.description ? ": " + event.description : ""}${event.location ? " at " + event.location : ""}`}
                tabIndex={0}
                title={`${event.title}${event.description ? "\n" + event.description : ""}${event.location ? "\n" + event.location : ""}`}
                style={{
                  padding: "10px 12px",
                  borderBottom: index < events.length - 1 ? "1px solid rgba(255,255,255,0.1)" : "none",
                  display: "flex",
                  gap: "12px",
                  alignItems: "center",
                  cursor: "pointer",
                  transition: "background 0.2s",
                  flexShrink: 0,
                }}
                onMouseOver={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.04)";
                }}
                onMouseOut={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                }}
              >
                <div
                  style={{
                    minWidth: 70,
                    padding: "4px 8px",
                    background: "rgba(124, 246, 211, 0.1)",
                    border: "1px solid var(--accent)",
                    borderRadius: "6px",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: "var(--accent)",
                    textAlign: "center",
                    whiteSpace: "nowrap",
                  }}
                  aria-label={`Time until event: ${getTimeUntil(event.start_time)}`}
                >
                  {getTimeUntil(event.start_time)}
                </div>

                <div
                  style={{
                    flex: 1,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    minWidth: 0,
                  }}
                >
                  <div
                    style={{
                      fontWeight: 600,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {event.title}
                  </div>
                  <div
                    style={{
                      fontSize: "0.8rem",
                      opacity: 0.7,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {formatDateTime(event.start_time)}
                    {event.location && ` | ${event.location}`}
                  </div>
                </div>
              </article>
            ))
          )}
        </div>
      </div>
    </section>
  );
};

export default EventsPanelApp;
