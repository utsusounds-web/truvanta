import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE_URL } from "../api/client";

export type BackendHealth = "checking" | "reachable" | "unreachable";

/** Pings the backend on mount so connectivity problems show up
 * immediately on the login screen — before the person even types
 * anything — instead of only surfacing after a failed submit. Uses a
 * bare axios call (not the shared `client`) so it's never blocked by
 * the token-refresh interceptor, and a short timeout so a dead
 * server doesn't leave the banner in "checking" for long. */
export function useBackendHealth(): BackendHealth {
  const [status, setStatus] = useState<BackendHealth>("checking");

  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API_BASE_URL}/auth/me/`, { timeout: 6000, validateStatus: () => true })
      .then((res) => {
        // Any HTTP response at all (even 401) means the server is reachable —
        // only a network-level failure (caught below) means it isn't.
        if (!cancelled) setStatus(res.status ? "reachable" : "unreachable");
      })
      .catch(() => {
        if (!cancelled) setStatus("unreachable");
      });
    return () => { cancelled = true; };
  }, []);

  return status;
}
