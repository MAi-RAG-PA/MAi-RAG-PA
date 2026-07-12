// frontend/src/api/calendar.ts
import api from "./client";

export async function getUpcomingEvents(limit: number = 20) {
  const response = await api.get(`/api/memory/sqlite/events/upcoming?limit=${limit}`);
  return response.data;
}

export async function createEvent(event: {
  id?: string;
  title: string;
  description?: string;
  start_time: string;
  end_time?: string;
  location?: string;
  category?: string;
  is_recurring?: boolean;
  recurrence_type?: string;
  recurrence_days?: string[];
  recurrence_end_date?: string;
}) {
  const response = await api.post("/api/memory/sqlite/events", event);
  return response.data;
}

export async function deleteEvent(event_id: string) {
  const response = await api.delete(`/api/memory/sqlite/events/${event_id}`);
  return response.data;
}
