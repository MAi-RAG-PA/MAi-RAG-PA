import api from "./client";

export async function sendChat(query: string) {
  const response = await api.post("/chat", { query });
  return response.data;
}
