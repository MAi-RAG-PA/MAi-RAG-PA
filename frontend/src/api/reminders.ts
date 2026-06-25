import api from "./client";

export async function getReminders() {
  const response = await api.get("/reminders");
  return response.data;
}

export async function createReminder(reminder: {
  reminder_id: string;
  message: string;
  run_date: string;
}) {
  const response = await api.post("/reminders", reminder);
  return response.data;
}

export async function deleteReminder(reminder_id: string) {
  const response = await api.delete(`/reminders/${reminder_id}`);
  return response.data;
}
