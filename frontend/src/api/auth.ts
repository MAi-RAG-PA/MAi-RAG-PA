import api, { setAuthToken } from "./client";

export async function login(username: string, password: string) {
  const body = new URLSearchParams();
  body.append("username", username);
  body.append("password", password);

  const response = await api.post("/token", body, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  const token = response.data.access_token;
  setAuthToken(token);
  localStorage.setItem("token", token);
  return token;
}

export function logout() {
  setAuthToken(null);
  localStorage.removeItem("token");
}
