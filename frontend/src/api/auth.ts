// frontend/src/api/auth.ts
import api from "./client";

export async function getAuthStatus() {
  const response = await api.get("/api/auth/status");
  return response.data;
}

export async function generateApiKey() {
  const response = await api.post("/api/auth/generate-key");
  return response.data;
}

export async function revokeApiKey() {
  const response = await api.delete("/api/auth/key");
  return response.data;
}

export async function getAutoKey() {
  const response = await api.get("/api/auth/auto-key");
  return response.data;
}
