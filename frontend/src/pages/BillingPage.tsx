import { useEffect, useState, useCallback } from "react";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import { useAuth } from "../context/AuthContext";
import { getPlans, getMySubscription, subscribeToPlan, cancelMySubscription } from "../api/billing";
import type { Plan, Subscription } from "../api/billing";
import { formatMoney, formatDate, extractErrorMessage } from "../lib/format";
import "./BillingPage.css";

export default function BillingPage() {
  const { isOwnerOrAdmin } = useAuth();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyPlanId, setBusyPlanId] = useState<string | null>(null);
  const [canceling, setCanceling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    Promise.allSettled([getPlans(), getMySubscription()]).then(([p, s]) => {
      if (p.status === "fulfilled") setPlans(p.value); else console.error("Failed to load plans:", p.reason);
      if (s.status === "fulfilled") setSubscription(s.value); else console.error("Failed to load subscription:", s.reason);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(refresh, [refresh]);

  // After returning from Paystack checkout, the webhook that fully
  // activates the subscription may land a moment after the redirect —
  // poll briefly instead of showing a stale "not subscribed" state.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (!params.get("reference") && !params.get("trxref")) return;
    setActivating(true);
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts += 1;
      const s = await getMySubscription();
      setSubscription(s);
      if (s.status === "active" || attempts >= 6) {
        clearInterval(interval);
        setActivating(false);
        window.history.replaceState({}, "", window.location.pathname);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  async function handleSubscribe(plan: Plan) {
    setBusyPlanId(plan.id);
    setError(null);
    try {
      const callbackUrl = `${window.location.origin}/billing`;
      const { checkout_url } = await subscribeToPlan(plan.id, callbackUrl);
      window.location.href = checkout_url;
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't start checkout."));
      setBusyPlanId(null);
    }
  }

  async function handleCancel() {
    if (!window.confirm("Cancel your subscription? You'll keep access until the current period ends.")) return;
    setCanceling(true);
    setError(null);
    try {
      const s = await cancelMySubscription();
      setSubscription(s);
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't cancel subscription."));
    } finally {
      setCanceling(false);
    }
  }

  const currentPlanId = subscription?.status === "active" ? subscription.plan?.id : null;

  if (!isOwnerOrAdmin()) {
    return (
      <div>
        <PageHeader title="Billing" subtitle="Owner/admin only." />
        <EmptyState title="Owner/admin only" subtitle="Billing and subscription plans are managed by the business owner or admin." />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Billing" subtitle="Manage your plan and see what's unlocked." />

      {activating && (
        <div className="card" style={{ padding: 16, marginBottom: 20 }}>
          Confirming your payment — this usually takes a few seconds…
        </div>
      )}

      {subscription && subscription.status !== "none" && (
        <div className="card" style={{ padding: 20, marginBottom: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
            <div>
              <div className="section-title" style={{ marginBottom: 4 }}>
                {subscription.status === "trialing" ? "Free trial" : `Current plan: ${subscription.plan?.name || "—"}`}{" "}
                <span className={`badge badge--${subscription.status === "active" ? "good" : subscription.status === "trialing" ? "good" : subscription.status === "past_due" ? "attention" : "neutral"}`}>
                  {subscription.status === "trialing" ? "active" : subscription.status.replace("_", " ")}
                </span>
              </div>
              {subscription.current_period_end && (
                <p style={{ fontSize: 14.5, color: "var(--ink-300)", margin: 0 }}>
                  {subscription.status === "trialing"
                    ? `Full access to every feature until ${formatDate(subscription.current_period_end)} — pick a plan below any time before then, or after, to keep it going.`
                    : `${subscription.cancel_at_period_end ? "Access ends" : "Renews"} ${formatDate(subscription.current_period_end)}`}
                </p>
              )}
            </div>
            {subscription.status === "active" && !subscription.cancel_at_period_end && (
              <button className="btn btn-ghost" onClick={handleCancel} disabled={canceling}>
                {canceling ? "Canceling…" : "Cancel subscription"}
              </button>
            )}
          </div>
        </div>
      )}

      {error && <p className="inline-error" style={{ marginBottom: 16 }}>{error}</p>}

      {loading ? (
        <div className="loading-row">Loading…</div>
      ) : plans.length === 0 ? (
        <EmptyState title="No plans available yet" subtitle="Check back soon." />
      ) : (
        <div className="plan-grid">
          {plans.map((plan) => {
            const isCurrent = plan.id === currentPlanId;
            return (
              <div key={plan.id} className={`plan-card ${isCurrent ? "plan-card--current" : ""}`}>
                {isCurrent && <div className="plan-card-badge">Your plan</div>}
                <div className="plan-card-name">{plan.name}</div>
                <div className="plan-card-price">
                  {formatMoney(plan.price_amount, plan.currency)}
                  <span className="plan-card-interval">/{plan.billing_interval === "monthly" ? "mo" : "yr"}</span>
                </div>
                {plan.description && <p className="plan-card-desc">{plan.description}</p>}
                <ul className="plan-card-features">
                  {plan.features.map((f) => <li key={f.id}>{f.name}</li>)}
                </ul>
                <button
                  className={`btn ${isCurrent ? "btn-ghost" : "btn-primary"}`}
                  style={{ width: "100%" }}
                  disabled={isCurrent || busyPlanId === plan.id}
                  onClick={() => handleSubscribe(plan)}
                >
                  {isCurrent ? "Current plan" : busyPlanId === plan.id ? "Redirecting…" : "Subscribe"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
