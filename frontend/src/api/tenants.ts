import client from "./client";
import type { OnboardingFormState } from "../types/business";

export interface BusinessResponse {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  theme_color: string;
  business_type: string;
  currency_code: string;
}

export async function createBusiness(form: OnboardingFormState): Promise<{
  business: BusinessResponse;
  default_branch: { id: string; name: string };
}> {
  const fd = new FormData();
  fd.append("name", form.name);
  fd.append("business_type", form.business_type);
  fd.append("currency_code", form.currency_code);
  fd.append("timezone", form.timezone);
  fd.append("address", form.address);
  fd.append("phone_number", form.phone_number);
  fd.append("email", form.email);
  fd.append("receipt_header_note", form.receipt_header_note);
  fd.append("receipt_footer_note", form.receipt_footer_note);
  if (form.logoFile) fd.append("logo", form.logoFile);

  const res = await client.post("/tenants/businesses/", fd);
  return res.data;
}

export interface BusinessSettings extends BusinessResponse {
  notification_whatsapp_number: string;
  notification_email: string;
  ai_addon_enabled: boolean;
  paystack_public_key: string;
  paystack_configured: boolean;
  away_mode_enabled: boolean;
  away_mode_discount_threshold_percent: string | null;
  away_mode_refund_threshold_amount: string | null;
  away_mode_price_change_threshold_percent: string | null;
  default_tax_rate_percent: string | null;
  signup_code: string;
  support_access_expires_at: string | null;
}

export const getBusiness = (id: string) =>
  client.get<BusinessSettings>(`/tenants/businesses/${id}/`).then((r) => r.data);

export const updateBusinessSettings = (id: string, data: Partial<{
  notification_whatsapp_number: string; notification_email: string;
  paystack_public_key: string; paystack_secret_key: string;
  away_mode_enabled: boolean;
  away_mode_discount_threshold_percent: string | null;
  away_mode_refund_threshold_amount: string | null;
  away_mode_price_change_threshold_percent: string | null;
  default_tax_rate_percent: string | null;
  theme_color: string;
}>) => client.patch<BusinessSettings>(`/tenants/businesses/${id}/`, data).then((r) => r.data);

// Logo is a file, so it needs its own multipart request rather than
// riding along with the JSON PATCH above.
export const updateBusinessLogo = (id: string, logo: File) => {
  const fd = new FormData();
  fd.append("logo", logo);
  return client.patch<BusinessSettings>(`/tenants/businesses/${id}/`, fd).then((r) => r.data);
};

// --- Platform integrations (staff-only) ---
export interface PlatformSettings {
  whatsapp_phone_number_id: string;
  whatsapp_configured: boolean;
  email_host_user: string;
  email_configured: boolean;
  platform_paystack_public_key: string;
  paystack_configured: boolean;
  rent_mode_enabled: boolean;
  universal_color: string;
  minimum_client_version: string;
  google_oauth_client_id: string;
  trial_grace_days: number;
  trial_grace_feature_count: number;
  updated_at: string;
}

export const getPlatformSettings = () =>
  client.get<PlatformSettings>("/platform-settings/").then((r) => r.data);

// Public — no auth needed. The one slice of platform settings anyone
// can read, so the universal accent color can apply even on the
// login screen before anyone is authenticated.
export const getPlatformBranding = () =>
  client.get<{ universal_color: string; minimum_client_version: string; google_oauth_client_id: string }>("/platform-branding/").then((r) => r.data);

export const updatePlatformSettings = (data: Partial<{
  whatsapp_access_token: string; whatsapp_phone_number_id: string;
  email_host_user: string; email_host_password: string;
  platform_paystack_public_key: string; platform_paystack_secret_key: string;
  rent_mode_enabled: boolean;
  universal_color: string;
  minimum_client_version: string;
  google_oauth_client_id: string;
  trial_grace_days: number;
  trial_grace_feature_count: number;
}>) => client.patch<PlatformSettings>("/platform-settings/", data).then((r) => r.data);

// --- Feature layout: which dashboard each feature currently lives under ---
export const getFeatureLayout = () =>
  client.get<{ feature_hubs: Record<string, string> }>("/feature-layout/").then((r) => r.data.feature_hubs);

export interface AdminFeatureLayoutEntry {
  key: string;
  default_hub: string;
  current_hub: string;
}

export const getAdminFeatureLayout = () =>
  client.get<{ features: AdminFeatureLayoutEntry[]; hubs: string[] }>("/admin/feature-layout/").then((r) => r.data);

export const updateAdminFeatureLayout = (featureKey: string, hub: string) =>
  client.patch<AdminFeatureLayoutEntry>("/admin/feature-layout/", { feature_key: featureKey, hub }).then((r) => r.data);

export interface BackupLog {
  id: string;
  started_at: string;
  completed_at: string | null;
  status: "success" | "failed";
  filename: string;
  size_bytes: number | null;
  error: string;
}

/** Powers the "last backed up" indicator in Platform Admin. 404s with
 * no backups recorded yet — treated as null, not an error, by callers. */
export const getLatestBackup = () =>
  client.get<BackupLog>("/backups/latest/").then((r) => r.data).catch((err) => {
    if (err?.response?.status === 404) return null;
    throw err;
  });

// --- Branches joining an existing business via signup code ---
export const regenerateSignupCode = (businessId: string) =>
  client.post<BusinessSettings>(`/tenants/businesses/${businessId}/regenerate-signup-code/`).then((r) => r.data);

export interface BranchJoinRequest {
  id: string;
  business: string;
  branch_name: string;
  status: "pending" | "approved" | "rejected";
  requested_by: string;
  requested_by_email: string;
  requested_by_name: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_branch: string | null;
  created_at: string;
}

export const submitBranchJoinRequest = (signup_code: string, branch_name: string) =>
  client.post<BranchJoinRequest>("/tenants/branch-join-requests/submit/", { signup_code, branch_name }).then((r) => r.data);

export const getBranchJoinRequests = () =>
  client.get<BranchJoinRequest[]>("/tenants/branch-join-requests/").then((r) => {
    const data: any = r.data;
    return Array.isArray(data) ? data : data.results;
  });

export const approveBranchJoinRequest = (id: string) =>
  client.post<BranchJoinRequest>(`/tenants/branch-join-requests/${id}/approve/`).then((r) => r.data);

export const rejectBranchJoinRequest = (id: string) =>
  client.post<BranchJoinRequest>(`/tenants/branch-join-requests/${id}/reject/`).then((r) => r.data);

// --- Platform-support access: owner-granted, time-limited, revocable ---
export const grantSupportAccess = (hours: number) =>
  client.post<{ support_access_expires_at: string }>("/tenants/support-access/grant/", { hours }).then((r) => r.data);

export const revokeSupportAccess = () =>
  client.post<{ support_access_expires_at: null }>("/tenants/support-access/revoke/").then((r) => r.data);

// Staff-only: only succeeds while the target business currently has an open grant.
export const adminSupportLogin = (businessId: string) =>
  client.post<{ business_id: string; business_name: string }>("/tenants/support-access/login/", { business_id: businessId }).then((r) => r.data);

// --- Admin console quick-access PIN (staff-only, no shipped default) ---
export const getAdminPinStatus = () =>
  client.get<{ pin_is_set: boolean }>("/admin-pin/status/").then((r) => r.data);

export const unlockAdminPin = (pin: string) =>
  client.post<{ status: string; detail?: string }>("/admin-pin/unlock/", { pin }).then((r) => r.data);

export const changeAdminPin = (pin: string) =>
  client.post<{ status: string }>("/admin-pin/change/", { pin }).then((r) => r.data);
