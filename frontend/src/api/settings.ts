// frontend/src/api/settings.ts
import api from "./client";

export async function getSystemPrompt() {
  const response = await api.get("/api/settings/system-prompt");
  return response.data;
}

export async function setSystemPrompt(prompt: string) {
  const response = await api.post("/api/settings/system-prompt", {
    content: prompt,
  });
  return response.data;
}

export async function getHeartbeatSettings() {
  const response = await api.get("/api/settings/heartbeat");
  return response.data;
}

export async function setHeartbeatInterval(minutes: number) {
  const response = await api.post("/api/settings/heartbeat", {
    interval: minutes,
  });
  return response.data;
}

export async function getNotificationSettings() {
  const response = await api.get("/api/settings/notifications");
  return response.data;
}

export async function saveNotificationSettings(intervals: any[]) {
  const response = await api.post("/api/settings/notifications", {
    intervals,
  });
  return response.data;
}

export async function getDefaultModel() {
  const response = await api.get("/api/settings/default-model");
  return response.data;
}

export async function setDefaultModel(model: string) {
  const response = await api.post("/api/settings/default-model", {
    model,
  });
  return response.data;
}
