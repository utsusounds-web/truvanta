import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Navigate } from "react-router-dom";
import Field from "../components/Field";
import LogoDropzone from "../components/LogoDropzone";
import ReceiptPreview from "../components/ReceiptPreview";
import { useAuth } from "../context/AuthContext";
import { createBusiness, submitBranchJoinRequest } from "../api/tenants";
import { extractErrorMessage } from "../lib/format";
import {
  BUSINESS_TYPES, CURRENCIES, emptyOnboardingForm,
  type OnboardingFormState,
} from "../types/business";
import "./OnboardingPage.css";

const STEPS = [
  { key: "basics", label: "Business basics" },
  { key: "contact", label: "Contact & location" },
  { key: "branding", label: "Branding" },
] as const;

type StepKey = (typeof STEPS)[number]["key"];
type EntryMode = "choice" | "new" | "join" | "join-submitted";

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setActiveBusiness, memberships, logout, loadMe } = useAuth();
  // A join link (Branches page → "Copy join link") carries the signup
  // code here via ?code= — skip straight to the join form, pre-filled,
  // instead of making them pick "Join as a branch" and retype it.
  const linkedCode = searchParams.get("code");
  const [entryMode, setEntryMode] = useState<EntryMode>(linkedCode ? "join" : "choice");
  const [stepIndex, setStepIndex] = useState(0);
  const [form, setForm] = useState<OnboardingFormState>(emptyOnboardingForm);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [signupCode, setSignupCode] = useState(linkedCode || "");
  const [branchName, setBranchName] = useState("");
  const [joinError, setJoinError] = useState<string | null>(null);
  const [joinSubmitting, setJoinSubmitting] = useState(false);

  const currentStep: StepKey = STEPS[stepIndex].key;

  // Defense in depth: if someone with an existing business lands here
  // directly (bookmarked URL, back button, etc.), never let them create
  // a second business by accident — send them to their real data instead.
  if (memberships.length > 0) return <Navigate to="/dashboard" replace />;

  function update<K extends keyof OnboardingFormState>(key: K, value: OnboardingFormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function validateStep(step: StepKey): boolean {
    const next: Record<string, string> = {};
    if (step === "basics" && !form.name.trim()) {
      next.name = "Give your business a name — it'll appear on every receipt.";
    }
    if (step === "contact" && form.phone_number && !/^[0-9+()\-\s]{6,}$/.test(form.phone_number)) {
      next.phone_number = "That doesn't look like a valid phone number.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function goNext() {
    if (!validateStep(currentStep)) return;
    setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
  }

  function goBack() {
    setStepIndex((i) => Math.max(i - 1, 0));
  }

  function handleLogoSelect(file: File) {
    const url = URL.createObjectURL(file);
    setForm((f) => ({ ...f, logoFile: file, logoPreviewUrl: url }));
  }

  function handleLogoClear() {
    setForm((f) => ({ ...f, logoFile: null, logoPreviewUrl: null }));
  }

  const [businessJustCreated, setBusinessJustCreated] = useState(false);
  const [checkingApproval, setCheckingApproval] = useState(false);

  useEffect(() => {
    if (entryMode !== "join-submitted") return;
    // Waiting for someone else (the owner) to act — polling here means
    // approval is picked up while this tab is still open, instead of
    // the only way forward being "sign out and back in and hope".
    const interval = setInterval(async () => {
      try {
        const { memberships: fresh } = await loadMe();
        if (fresh.length > 0) {
          localStorage.setItem("sbos_business_id", fresh[0].business);
          navigate("/dashboard");
        }
      } catch {
        // Quietly retry next interval — a dropped connection here
        // shouldn't surface as an error on a passive waiting screen.
      }
    }, 8000);
    return () => clearInterval(interval);
  }, [entryMode, loadMe, navigate]);

  async function handleCheckApprovalNow() {
    setCheckingApproval(true);
    try {
      const { memberships: fresh } = await loadMe();
      if (fresh.length > 0) {
        localStorage.setItem("sbos_business_id", fresh[0].business);
        navigate("/dashboard");
      }
    } finally {
      setCheckingApproval(false);
    }
  }

  async function handleSubmit() {
    if (!validateStep("basics")) { setStepIndex(0); return; }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const { business } = await createBusiness(form);
      setActiveBusiness(business.id);
      // One more question before landing on the dashboard — see the
      // businessJustCreated screen below. Skipping straight to
      // /dashboard here would silently assume every business starts
      // at zero, which isn't true for someone already running one.
      setBusinessJustCreated(true);
    } catch (err: any) {
      setSubmitError(extractErrorMessage(err, "Couldn't set up your business. Check the details and try again."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleJoinSubmit() {
    if (!signupCode.trim() || !branchName.trim()) {
      setJoinError("Both the signup code and a name for your branch are required.");
      return;
    }
    setJoinSubmitting(true);
    setJoinError(null);
    try {
      await submitBranchJoinRequest(signupCode.trim(), branchName.trim());
      setEntryMode("join-submitted");
    } catch (err: any) {
      setJoinError(extractErrorMessage(err, "Couldn't submit that request."));
    } finally {
      setJoinSubmitting(false);
    }
  }

  if (entryMode === "choice") {
    return (
      <div className="onboarding-shell">
        <div className="onboarding-form-col">
          <div className="onboarding-header">
            <h1 className="display">Welcome to Truvanta</h1>
            <p className="onboarding-subhead">Are you setting up a new business, or joining one that already uses Truvanta as one of its branches?</p>
          </div>
          <div className="onboarding-card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <button type="button" className="btn btn-primary" style={{ padding: "16px 20px", textAlign: "left" }} onClick={() => setEntryMode("new")}>
              <strong>Set up a new business</strong>
              <div style={{ fontWeight: 400, fontSize: 15, opacity: 0.85, marginTop: 4 }}>I'm the owner, starting fresh.</div>
            </button>
            <button type="button" className="btn btn-ghost" style={{ padding: "16px 20px", textAlign: "left", border: "1px solid var(--line)" }} onClick={() => setEntryMode("join")}>
              <strong>Join as a branch</strong>
              <div style={{ fontWeight: 400, fontSize: 15, opacity: 0.85, marginTop: 4 }}>My business already has a Truvanta account, and I have a signup code from the owner.</div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (entryMode === "join") {
    return (
      <div className="onboarding-shell">
        <div className="onboarding-form-col">
          <div className="onboarding-header">
            <h1 className="display">Join as a branch</h1>
            <p className="onboarding-subhead">
              Get the signup code from your business owner. Once you submit, they'll need to approve
              your branch before you can start using it — you won't have access until then.
            </p>
          </div>
          <div className="onboarding-card">
            <Field label="Signup code" hint="Given to you by your business owner">
              <input
                className="input"
                placeholder="e.g. 7K2QX9LM"
                value={signupCode}
                onChange={(e) => setSignupCode(e.target.value.toUpperCase())}
                style={{ letterSpacing: "0.08em", fontFamily: "var(--font-mono)" }}
              />
            </Field>
            <Field label="This branch's name" hint="e.g. the location or area it's in">
              <input
                className="input"
                placeholder="e.g. Wuse Branch"
                value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
              />
            </Field>
            {joinError && <p className="onboarding-error">{joinError}</p>}
            <div className="onboarding-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setEntryMode("choice")} disabled={joinSubmitting}>
                Back
              </button>
              <div className="spacer" />
              <button type="button" className="btn btn-primary" onClick={handleJoinSubmit} disabled={joinSubmitting}>
                {joinSubmitting ? "Submitting…" : "Submit request"}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (businessJustCreated) {
    return (
      <div className="onboarding-shell">
        <div className="onboarding-form-col">
          <div className="onboarding-header">
            <h1 className="display">One more thing</h1>
            <p className="onboarding-subhead">
              Is this a brand new business, or one that's already running?
            </p>
          </div>
          <div className="onboarding-card">
            <button
              type="button" className="btn btn-primary" style={{ width: "100%", marginBottom: 10 }}
              onClick={() => navigate("/opening-balance")}
            >
              I already have a business — I have stock, customers, or money to account for
            </button>
            <button
              type="button" className="btn btn-ghost" style={{ width: "100%" }}
              onClick={() => navigate("/dashboard")}
            >
              Just starting out — I'm beginning with nothing yet
            </button>
            <p style={{ fontSize: 14, color: "var(--ink-300)", textAlign: "center", marginTop: 14 }}>
              You can always do this later from Business Health → Opening Balance.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (entryMode === "join-submitted") {
    return (
      <div className="onboarding-shell">
        <div className="onboarding-form-col">
          <div className="onboarding-header">
            <h1 className="display">Request sent</h1>
            <p className="onboarding-subhead">
              Your request to join as "{branchName}" has been sent to the business owner for approval.
              This page checks automatically every few seconds — or check right now below.
            </p>
          </div>
          <div className="onboarding-card">
            <button type="button" className="btn btn-primary" style={{ width: "100%", marginBottom: 10 }} onClick={handleCheckApprovalNow} disabled={checkingApproval}>
              {checkingApproval ? "Checking…" : "Check now"}
            </button>
            <button type="button" className="btn btn-ghost" style={{ width: "100%" }} onClick={() => logout()}>
              Sign out
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="onboarding-shell">
      <div className="onboarding-form-col">
        <div className="onboarding-header">
          <h1 className="display">Set up your business</h1>
          <p className="onboarding-subhead">
            A few details now save you from a developer later — your logo and info will show on every receipt, invoice, and report.
          </p>
        </div>

        <ol className="step-rail" aria-label="Setup steps">
          {STEPS.map((s, i) => (
            <li
              key={s.key}
              className={`step-item ${i === stepIndex ? "step-item--active" : ""} ${i < stepIndex ? "step-item--done" : ""}`}
            >
              <span className="step-dot">{i < stepIndex ? "✓" : i + 1}</span>
              <span>{s.label}</span>
            </li>
          ))}
        </ol>

        <div className="onboarding-card">
          {currentStep === "basics" && (
            <>
              <Field label="Business name" required error={errors.name}>
                <input
                  className="input"
                  placeholder="e.g. Blessing Provisions Store"
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                />
              </Field>
              <Field label="Business type">
                <select className="input" value={form.business_type} onChange={(e) => update("business_type", e.target.value)}>
                  {BUSINESS_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </Field>
              <Field label="Currency">
                <select className="input" value={form.currency_code} onChange={(e) => update("currency_code", e.target.value)}>
                  {CURRENCIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </Field>
            </>
          )}

          {currentStep === "contact" && (
            <>
              <Field label="Address" hint="Shown on receipts and invoices">
                <textarea
                  className="input"
                  rows={2}
                  placeholder="Shop 14, Wuse Market, Abuja"
                  value={form.address}
                  onChange={(e) => update("address", e.target.value)}
                />
              </Field>
              <Field label="Phone number" error={errors.phone_number}>
                <input
                  className="input"
                  placeholder="080X XXX XXXX"
                  value={form.phone_number}
                  onChange={(e) => update("phone_number", e.target.value)}
                />
              </Field>
              <Field label="Email" hint="Optional — for reports and account recovery">
                <input
                  className="input"
                  type="email"
                  placeholder="you@business.com"
                  value={form.email}
                  onChange={(e) => update("email", e.target.value)}
                />
              </Field>
            </>
          )}

          {currentStep === "branding" && (
            <>
              <Field label="Logo" hint="Appears on every receipt, invoice, and report header">
                <LogoDropzone
                  previewUrl={form.logoPreviewUrl}
                  onSelect={handleLogoSelect}
                  onClear={handleLogoClear}
                />
              </Field>
              <Field label="Receipt header note" hint="A short line under your business name, e.g. a tagline">
                <input
                  className="input"
                  placeholder="Quality groceries, fair prices"
                  value={form.receipt_header_note}
                  onChange={(e) => update("receipt_header_note", e.target.value)}
                />
              </Field>
              <Field label="Receipt footer note" hint="Shown at the bottom of every receipt">
                <input
                  className="input"
                  value={form.receipt_footer_note}
                  onChange={(e) => update("receipt_footer_note", e.target.value)}
                />
              </Field>
            </>
          )}

          {submitError && <p className="onboarding-error">{submitError}</p>}

          <div className="onboarding-actions">
            {stepIndex > 0 && (
              <button type="button" className="btn btn-ghost" onClick={goBack} disabled={submitting}>
                Back
              </button>
            )}
            <div className="spacer" />
            {stepIndex < STEPS.length - 1 ? (
              <button type="button" className="btn btn-primary" onClick={goNext}>
                Continue
              </button>
            ) : (
              <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Setting up…" : "Finish setup"}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="onboarding-preview-col">
        <ReceiptPreview form={form} />
      </div>
    </div>
  );
}
