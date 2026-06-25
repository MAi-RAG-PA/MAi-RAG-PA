//* frontend/src/api/settings.ts

import api from "./client";

export async function getSystemPrompt() {
  const response = await api.get("/system_prompt");
  return response.data;
}

export async function setSystemPrompt(prompt: string) {
  const response = await api.post("/system_prompt", {
    filename: "system_prompt",
    content: prompt,
  }, {
    headers: { "Content-Type": "application/json" },
  });
  return response.data;
}

export async function setHeartbeatInterval(minutes: number) {
  const response = await api.post("/heartbeat/interval", minutes, {
    headers: { "Content-Type": "application/json" },
  });
  return response.data;
}
setSystemPrompt
