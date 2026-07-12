// frontend/src/api/reminders.ts
import api from "./client";

export async function getUpcomingReminders(limit: number = 20) {
  const response = await api.get(`/api/memory/sqlite/reminders/upcoming?limit=${limit}`);
  return response.data;
}

export async function createReminder(reminder: {
  id?: string;
  text: string;
  due_time: string;
  priority?: string;
  completed?: boolean;
}) {
  const response = await api.post("/api/memory/sqlite/reminders", reminder);
  return response.data;
}

export async function deleteReminder(reminder_id: string) {
  const response = await api.delete(`/api/memory/sqlite/reminders/${reminder_id}`);
  return response.data;
}

export async function checkDueAlerts() {
  const response = await api.get("/api/memory/sqlite/reminders/check-alerts");
  return response.data;
}
