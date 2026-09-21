import client from "./client";

export const getDuressPasswordStatus = () =>
  client.get<{ is_set_up: boolean }>("/auth/duress-password/").then((r) => r.data);

export const setDuressPassword = (currentPassword: string, duressPassword: string) =>
  client.post("/auth/duress-password/", { current_password: currentPassword, duress_password: duressPassword });

export const removeDuressPassword = (currentPassword: string) =>
  client.delete("/auth/duress-password/", { data: { current_password: currentPassword } });
