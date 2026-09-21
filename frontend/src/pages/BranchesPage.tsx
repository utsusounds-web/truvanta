import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { getBranches, createBranch, updateBranch } from "../api/resources";
import type { Branch } from "../api/types";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import { extractErrorMessage, formatDate } from "../lib/format";
import {
  getBusiness, regenerateSignupCode, getBranchJoinRequests,
  approveBranchJoinRequest, rejectBranchJoinRequest, type BranchJoinRequest,
} from "../api/tenants";

const emptyForm = { name: "", address: "", phone_number: "", parent_branch: "" };

export default function BranchesPage() {
  const { refresh: refreshBusinessContext } = useBusiness();
  const { isOwnerOrAdmin } = useAuth();
  const allowed = isOwnerOrAdmin();
  const businessId = localStorage.getItem("sbos_business_id") || "";
  const [branches, setBranches] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Branch | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [signupCode, setSignupCode] = useState<string | null>(null);
  const [codeCopied, setCodeCopied] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [joinRequests, setJoinRequests] = useState<BranchJoinRequest[]>([]);
  const [joinRequestsLoading, setJoinRequestsLoading] = useState(true);
  const [joinActionId, setJoinActionId] = useState<string | null>(null);
  const [joinError, setJoinError] = useState<string | null>(null);

  function refresh() {
    setLoading(true);
    getBranches().then(setBranches).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  function refreshJoinRequests() {
    if (!allowed) { setJoinRequestsLoading(false); return; }
    setJoinRequestsLoading(true);
    getBranchJoinRequests().then(setJoinRequests).finally(() => setJoinRequestsLoading(false));
  }
  useEffect(refreshJoinRequests, [allowed]);

  useEffect(() => {
    if (!allowed || !businessId) return;
    getBusiness(businessId).then((b) => setSignupCode(b.signup_code));
  }, [allowed, businessId]);

  async function handleCopyCode() {
    if (!signupCode) return;
    await navigator.clipboard.writeText(signupCode);
    setCodeCopied(true);
    setTimeout(() => setCodeCopied(false), 2000);
  }

  async function handleCopyJoinLink() {
    if (!signupCode) return;
    const link = `${window.location.origin}/auth?code=${encodeURIComponent(signupCode)}`;
    await navigator.clipboard.writeText(link);
    setLinkCopied(true);
    setTimeout(() => setLinkCopied(false), 2000);
  }

  async function handleRegenerateCode() {
    if (!window.confirm("Regenerate the signup code? The old code will stop working immediately — anyone who had it will need the new one.")) return;
    setRegenerating(true);
    try {
      const updated = await regenerateSignupCode(businessId);
      setSignupCode(updated.signup_code);
    } finally {
      setRegenerating(false);
    }
  }

  async function handleApprove(id: string) {
    setJoinActionId(id); setJoinError(null);
    try {
      await approveBranchJoinRequest(id);
      refreshJoinRequests();
      refresh();
      refreshBusinessContext();
    } catch (err: any) {
      setJoinError(extractErrorMessage(err, "Couldn't approve that request."));
    } finally {
      setJoinActionId(null);
    }
  }

  async function handleReject(id: string) {
    setJoinActionId(id); setJoinError(null);
    try {
      await rejectBranchJoinRequest(id);
      refreshJoinRequests();
    } catch (err: any) {
      setJoinError(extractErrorMessage(err, "Couldn't reject that request."));
    } finally {
      setJoinActionId(null);
    }
  }

  const pendingRequests = joinRequests.filter((r) => r.status === "pending");

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError(null);
    setShowModal(true);
  }

  function openEdit(b: Branch) {
    setEditing(b);
    setForm({ name: b.name, address: b.address, phone_number: b.phone_number, parent_branch: b.parent_branch || "" });
    setError(null);
    setShowModal(true);
  }

  async function handleSave() {
    if (!form.name.trim()) { setError("Branch name is required."); return; }
    // Renaming an existing branch (as opposed to adding a new one) is a
    // real, meaningful action — it changes what every membership/report
    // tied to this branch calls it, not just a cosmetic label. Making
    // this explicit here is what stops "I wanted to add a branch" from
    // silently turning into "I renamed Main Branch" instead.
    if (editing && form.name.trim() !== editing.name) {
      const confirmed = window.confirm(
        `This renames "${editing.name}" to "${form.name.trim()}" — it does not create a new branch. ` +
        `Everyone already assigned to "${editing.name}" will now see it as "${form.name.trim()}". ` +
        `If you meant to add a separate new branch, cancel this and use "Add branch" instead.\n\nContinue with the rename?`
      );
      if (!confirmed) return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = { ...form, parent_branch: form.parent_branch || null };
      if (editing) await updateBranch(editing.id, payload);
      else await createBranch(payload);
      setShowModal(false);
      refresh();
      refreshBusinessContext(); // so the sidebar's branch switcher picks up the new branch immediately
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't save branch."));
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleActive(b: Branch) {
    await updateBranch(b.id, { is_active: !b.is_active });
    refresh();
  }

  const mainBranches = branches.filter((b) => !b.parent_branch);
  const subBranchesOf = (id: string) => branches.filter((b) => b.parent_branch === id);

  return (
    <div>
      <PageHeader
        title="Branches"
        subtitle="Every location your business operates from. Group locations under a main branch if you have many."
        actions={allowed ? <button className="btn btn-primary" onClick={openCreate}>Add branch</button> : undefined}
      />

      {allowed && (
        <div className="card" style={{ padding: 20, marginBottom: 20, maxWidth: 560 }}>
          <h2 className="section-title">Giving a branch its own login</h2>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 14 }}>
            First add the branch above, then go to <strong>Staff</strong> and set up a login for it
            yourself — you choose the email and password and hand them over directly. You also
            decide there exactly what that login can see: just this branch, or all of them.
          </p>
          <Link to="/staff" className="btn btn-primary">Go to Staff →</Link>

          <details style={{ marginTop: 18 }}>
            <summary style={{ cursor: "pointer", fontSize: 13.5, color: "var(--ink-300)" }}>
              Prefer they register themselves instead?
            </summary>
            <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--line)" }}>
              <p style={{ fontSize: 13.5, color: "var(--ink-600)", marginBottom: 14 }}>
                Give this code — or the join link, which takes them straight to sign-up with it
                pre-filled — to a new location's staff so they can register it as a branch of your
                business themselves. You still approve every request below before they get any access.
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                <code style={{ fontFamily: "var(--font-mono)", fontSize: 18, letterSpacing: "0.1em", background: "var(--paper-100)", padding: "8px 14px", borderRadius: "var(--radius-sm)" }}>
                  {signupCode || "…"}
                </code>
                <button className="btn btn-ghost" onClick={handleCopyCode} disabled={!signupCode}>
                  {codeCopied ? "Copied!" : "Copy"}
                </button>
                <button className="btn btn-ghost" onClick={handleCopyJoinLink} disabled={!signupCode}>
                  {linkCopied ? "Link copied!" : "Copy join link"}
                </button>
                <button className="btn btn-ghost" onClick={handleRegenerateCode} disabled={regenerating || !signupCode}>
                  {regenerating ? "Regenerating…" : "Regenerate"}
                </button>
              </div>
            </div>
          </details>
        </div>
      )}

      {allowed && !joinRequestsLoading && pendingRequests.length > 0 && (
        <div className="card" style={{ padding: 0, marginBottom: 20 }}>
          <h2 className="section-title" style={{ padding: "18px 20px 0" }}>Pending branch requests</h2>
          {joinError && <p className="inline-error" style={{ padding: "0 20px" }}>{joinError}</p>}
          <table className="data-table">
            <thead><tr><th>Requested by</th><th>Branch name</th><th>Requested</th><th></th></tr></thead>
            <tbody>
              {pendingRequests.map((r) => (
                <tr key={r.id}>
                  <td>{r.requested_by_name}<div style={{ fontSize: 14, color: "var(--ink-300)" }}>{r.requested_by_email}</div></td>
                  <td>{r.branch_name}</td>
                  <td>{formatDate(r.created_at)}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn btn-primary" disabled={joinActionId === r.id} onClick={() => handleApprove(r.id)}>
                      {joinActionId === r.id ? "…" : "Approve"}
                    </button>{" "}
                    <button className="btn btn-ghost" disabled={joinActionId === r.id} onClick={() => handleReject(r.id)}>
                      Reject
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading ? (
        <div className="loading-row">Loading…</div>
      ) : branches.length === 0 ? (
        <EmptyState title="No branches yet" subtitle="Add your first branch to get started." />
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table">
            <thead><tr><th>Name</th><th>Address</th><th>Phone</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {mainBranches.map((b) => (
                <Fragment key={b.id}>
                  <tr>
                    <td>{b.name}</td>
                    <td>{b.address || "—"}</td>
                    <td>{b.phone_number || "—"}</td>
                    <td><span className={`badge ${b.is_active ? "badge--good" : "badge--neutral"}`}>{b.is_active ? "active" : "inactive"}</span></td>
                    <td style={{ textAlign: "right" }}>
                      <button className="btn btn-ghost" onClick={() => openEdit(b)}>Edit</button>{" "}
                      <button className="btn btn-ghost" onClick={() => toggleActive(b)}>{b.is_active ? "Deactivate" : "Activate"}</button>
                    </td>
                  </tr>
                  {subBranchesOf(b.id).map((sub) => (
                    <tr key={sub.id}>
                      <td style={{ paddingLeft: 32, color: "var(--ink-600)" }}>↳ {sub.name}</td>
                      <td>{sub.address || "—"}</td>
                      <td>{sub.phone_number || "—"}</td>
                      <td><span className={`badge ${sub.is_active ? "badge--good" : "badge--neutral"}`}>{sub.is_active ? "active" : "inactive"}</span></td>
                      <td style={{ textAlign: "right" }}>
                        <button className="btn btn-ghost" onClick={() => openEdit(sub)}>Edit</button>{" "}
                        <button className="btn btn-ghost" onClick={() => toggleActive(sub)}>{sub.is_active ? "Deactivate" : "Activate"}</button>
                      </td>
                    </tr>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <Modal title={editing ? "Edit branch" : "Add branch"} onClose={() => setShowModal(false)}>
          <Field label="Branch name" required>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Main Market Stall" />
          </Field>
          <Field label="Address"><input className="input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></Field>
          <Field label="Phone number"><input className="input" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} /></Field>
          <Field label="Part of a main branch?" hint="Leave blank if this is its own main branch — useful for grouping many small locations under one.">
            <select className="input" value={form.parent_branch} onChange={(e) => setForm({ ...form, parent_branch: e.target.value })}>
              <option value="">This is a main branch</option>
              {branches.filter((b) => b.id !== editing?.id && !b.parent_branch).map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSave} disabled={submitting}>
            {submitting ? "Saving…" : editing ? "Save changes" : "Add branch"}
          </button>
        </Modal>
      )}
    </div>
  );
}
