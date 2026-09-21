import client from "./client";

export interface UserSession {
  id: string;
  device_label: string;
  ip_address: string | null;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
}

export const getSessions = () => client.get<UserSession[]>("/auth/sessions/").then((r) => {
  const data: any = r.data;
  return Array.isArray(data) ? data : data.results;
});

export const revokeSession = (sessionId: string) =>
  client.post(`/auth/sessions/${sessionId}/revoke/`);

export const revokeOtherSessions = (currentSessionId: string | null) =>
  client.post<{ revoked: number }>("/auth/sessions/revoke-others/", { session_id: currentSessionId }).then((r) => r.data);

// Owner/admin only: every active session across every staff member of
// the current business — which device, which branch(es), last seen.
export interface StaffSession {
  id: string;
  user_email: string;
  user_name: string;
  role: string;
  branches: string[];
  device_label: string;
  ip_address: string | null;
  created_at: string;
  last_seen_at: string;
}

export const getBusinessStaffSessions = () =>
  client.get<StaffSession[]>("/auth/business-sessions/").then((r) => r.data);

export const revokeBusinessStaffSession = (sessionId: string) =>
  client.post(`/auth/business-sessions/${sessionId}/revoke/`);
