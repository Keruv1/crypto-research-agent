import axios from "axios";

// In dev, Vite proxies /api to http://localhost:8000 (see vite.config.js).
// Override with VITE_API_BASE for other setups.
const baseURL = import.meta.env.VITE_API_BASE || "";

const http = axios.create({ baseURL, timeout: 120000 });

export async function getBrief(coin) {
  const { data } = await http.post("/api/brief", { coin });
  return data;
}

export async function askQuestion(coin, question) {
  const { data } = await http.post("/api/ask", { coin, question });
  return data;
}

export async function checkHealth() {
  const { data } = await http.get("/api/health");
  return data;
}
