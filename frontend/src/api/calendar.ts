import api from "./client";

export async function getEvents() {
  const response = await api.get("/calendar/events");
  return response.data;
}

export async function createEvent(event: {
  title: string;
  description?: string | null;
  start_time: string;
  end_time?: string | null;
}) {
  const response = await api.post("/calendar/events", event);
  return response.data;
}
