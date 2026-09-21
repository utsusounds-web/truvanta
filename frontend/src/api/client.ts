import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const client = axios.create({ baseURL: API_BASE_URL, timeout: 20000 });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("sbos_access_token");
  const businessId = localStorage.getItem("sbos_business_id");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (businessId) config.headers["X-Business-ID"] = businessId;
  return config;
});

// Access tokens expire after 30 minutes (see backend SIMPLE_JWT). Without
// this, every request made after that point 401s with no recovery — the
// app looks "broken" or "won't let me in" mid-session even though the
// person is still logged in as far as they know. This transparently
// refreshes once and retries; only logs the person out if the refresh
// token itself is invalid/expired (14 days, or explicitly revoked).
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("sbos_refresh_token");
  if (!refreshToken) return null;
  try {
    const res = await axios.post(`${API_BASE_URL}/auth/login/refresh/`, { refresh: refreshToken });
    const newAccess = res.data.access;
    localStorage.setItem("sbos_access_token", newAccess);
    if (res.data.refresh) localStorage.setItem("sbos_refresh_token", res.data.refresh);
    return newAccess;
  } catch {
    return null;
  }
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint = originalRequest?.url?.includes("/auth/login");

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true;
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => { refreshPromise = null; });
      }
      const newAccess = await refreshPromise;
      if (newAccess) {
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return client(originalRequest);
      }
      // Refresh failed — the session is genuinely over, not just a blip.
      localStorage.removeItem("sbos_access_token");
      localStorage.removeItem("sbos_refresh_token");
      if (!window.location.pathname.startsWith("/auth")) {
        window.location.href = "/auth";
      }
    }
    return Promise.reject(error);
  }
);

export default client;
