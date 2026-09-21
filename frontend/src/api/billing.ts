import client from "./client";
import type { AuditLog } from "./types";

export interface Feature {
  id: string;
  key: string;
  name: string;
  description: string;
  category: string;
  is_active: boolean;
  lock_priority: number;
}

export interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  price_amount: string;
  currency: string;
  billing_interval: "weekly" | "monthly" | "yearly";
  features: Feature[];
  is_active: boolean;
  sort_order: number;
}

export interface Subscription {
  id: string;
  business: string;
  business_name: string;
  plan: Plan | null;
  status: "none" | "trialing" | "pending" | "active" | "past_due" | "canceled";
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  features: string[];
}

export interface FeatureOverride {
  id: string;
  business: string;
  business_name: string;
  feature: string;
  feature_key: string;
  is_enabled: boolean;
  note: string;
  granted_by_email: string | null;
  expires_at: string | null;
}

async function list<T>(url: string, params?: Record<string, string>): Promise<T[]> {
  const res = await client.get(url, { params });
  return Array.isArray(res.data) ? res.data : res.data.results;
}

// --- Business-facing: browse plans, manage own subscription ---------------

export const getPlans = () => list<Plan>("/billing/plans/");
export const getMySubscription = () => client.get<Subscription>("/billing/subscription/").then((r) => r.data);
export const subscribeToPlan = (planId: string, callbackUrl: string) =>
  client.post<{ checkout_url: string }>("/billing/subscription/subscribe/", { plan_id: planId, callback_url: callbackUrl }).then((r) => r.data);
export const cancelMySubscription = () =>
  client.post<Subscription>("/billing/subscription/cancel/").then((r) => r.data);

// --- Platform admin ---------------------------------------------------

export const adminGetFeatures = () => list<Feature>("/billing/admin/features/");
export const adminCreateFeature = (data: Partial<Feature>) =>
  client.post<Feature>("/billing/admin/features/", data).then((r) => r.data);
export const adminUpdateFeature = (id: string, data: Partial<Feature>) =>
  client.patch<Feature>(`/billing/admin/features/${id}/`, data).then((r) => r.data);

export const adminGetPlans = () => list<Plan>("/billing/admin/plans/");
export const adminCreatePlan = (data: {
  name: string; slug: string; description: string; price_amount: number; currency: string;
  billing_interval: string; sort_order: number; feature_ids: string[];
}) => client.post<Plan>("/billing/admin/plans/", data).then((r) => r.data);
export const adminUpdatePlan = (id: string, data: Partial<{
  name: string; description: string; price_amount: number; is_active: boolean;
  sort_order: number; feature_ids: string[];
}>) => client.patch<Plan>(`/billing/admin/plans/${id}/`, data).then((r) => r.data);

export const adminGetSubscriptions = () => list<Subscription>("/billing/admin/subscriptions/");
export const adminGetBusinesses = () =>
  client.get<{ id: string; name: string; is_active: boolean; support_access_expires_at: string | null; pending_deletion_at: string | null }[]>("/billing/admin/businesses/").then((r) => r.data);

export const adminGetOverrides = (businessId?: string) =>
  list<FeatureOverride>("/billing/admin/overrides/", businessId ? { business: businessId } : undefined);
export const adminCreateOverride = (data: { business: string; feature: string; is_enabled: boolean; note?: string; expires_at?: string | null }) =>
  client.post<FeatureOverride>("/billing/admin/overrides/", data).then((r) => r.data);
export const adminDeleteOverride = (id: string) => client.delete(`/billing/admin/overrides/${id}/`);

// --- Platform admin: usage analytics, direct subscription activation, broadcast ---

export interface PlatformUsageSummary {
  generated_at: string;
  totals: { businesses: number; branches: number; users: number; staff_memberships: number };
  activity: {
    active_users_last_7_days: number; active_users_last_30_days: number;
    businesses_that_made_a_sale_last_30_days: number; businesses_with_no_sale_last_30_days: number;
  };
  subscriptions: {
    by_status: Record<string, number>;
    by_plan: { plan_name: string; billing_interval: string; count: number }[];
  };
  signups_last_30_days: { date: string; count: number }[];
}

export const adminGetUsageAnalytics = () =>
  client.get<PlatformUsageSummary>("/billing/admin/usage-analytics/").then((r) => r.data);

export const adminActivateSubscription = (data: { business: string; plan: string; period_days?: number; note?: string }) =>
  client.post<Subscription>("/billing/admin/subscriptions/activate/", data).then((r) => r.data);

export const adminExtendTrial = (business: string, days: number) =>
  client.post<Subscription>("/billing/admin/subscriptions/extend-trial/", { business, days }).then((r) => r.data);

export interface TenantUsage {
  business_id: string;
  business_name: string;
  media_bytes: number;
  row_counts: Record<string, number>;
  total_rows: number;
}

export const adminGetTenantUsage = (businessId: string) =>
  client.get<TenantUsage>(`/billing/admin/tenants/${businessId}/usage/`).then((r) => r.data);

export const adminScheduleDeletion = (business: string, confirmName: string, graceDays = 7) =>
  client.post<{ id: string; pending_deletion_at: string }>(
    "/billing/admin/businesses/schedule-deletion/", { business, confirm_name: confirmName, grace_days: graceDays },
  ).then((r) => r.data);

export const adminCancelDeletion = (business: string) =>
  client.post<{ id: string; pending_deletion_at: null }>(
    "/billing/admin/businesses/cancel-deletion/", { business },
  ).then((r) => r.data);

export const adminExecutePurge = (business: string, confirmName: string) =>
  client.post<{ deleted: boolean; business_id: string; business_name: string }>(
    "/billing/admin/businesses/execute-purge/", { business, confirm_name: confirmName },
  ).then((r) => r.data);

export const adminFreezeAccount = (business: string, active: boolean) =>
  client.post<{ id: string; is_active: boolean }>("/billing/admin/businesses/freeze/", { business, active }).then((r) => r.data);

export const adminKillSwitch = (businessId: string) =>
  client.post<{ revoked: number }>("/auth/admin/kill-switch/", { business_id: businessId }).then((r) => r.data);

export const adminBroadcastNotification = (data: {
  title: string; message: string; level: "critical" | "important" | "info";
  target: "all" | "active_subscribers" | "specific"; business_ids?: string[];
}) => client.post<{ sent_to_businesses: number }>("/billing/admin/broadcast-notification/", data).then((r) => r.data);

export const adminGetAuditLogs = (params?: Record<string, string>) => list<AuditLog>("/admin/audit-logs/", params);

// --- Webhook log (Paystack), staff-only ---
export interface BillingEvent {
  id: string;
  business: string | null;
  business_name: string | null;
  event_type: string;
  paystack_reference: string;
  processed_ok: boolean;
  error: string;
  created_at: string;
}

export const adminGetWebhookEvents = (params?: Record<string, string>) =>
  list<BillingEvent>("/billing/admin/events/", params);

export const adminReplayWebhookEvent = (id: string) =>
  client.post<BillingEvent>(`/billing/admin/events/${id}/replay/`).then((r) => r.data);
