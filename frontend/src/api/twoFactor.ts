import client from "./client";

export const setupTwoFactor = () =>
  client.post<{ secret: string; qr_code: string; pending_token: string }>("/auth/2fa/setup/").then((r) => r.data);

export const confirmTwoFactor = (pendingToken: string, code: string) =>
  client.post("/auth/2fa/confirm/", { pending_token: pendingToken, code });

export const disableTwoFactor = (password: string) =>
  client.post("/auth/2fa/disable/", { password });
