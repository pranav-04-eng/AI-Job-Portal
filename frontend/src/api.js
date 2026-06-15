// Thin fetch wrapper around the API gateway (:8000). The gateway is the only
// origin the browser talks to; it proxies to the individual services.
const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TOKEN_KEY = "hv_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) =>
  t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY);

async function request(path, { method = "GET", body, form, auth = true } = {}) {
  const headers = {};
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = form; // browser sets multipart Content-Type + boundary
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(API + path, { method, headers, body: payload });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const msg = (data && data.detail) || res.statusText || "Request failed";
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  get: (p, o) => request(p, { ...o }),
  post: (p, body, o) => request(p, { method: "POST", body, ...o }),
  patch: (p, body, o) => request(p, { method: "PATCH", body, ...o }),
  postForm: (p, form, o) => request(p, { method: "POST", form, ...o }),
};

export { API };
