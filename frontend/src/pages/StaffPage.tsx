import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { useBusiness } from "../context/BusinessContext";
import { useAuth } from "../context/AuthContext";
import {
  getPermissionCatalog, getRoles, createRole, setRolePermissions,
  getMemberships, inviteStaff, updateMembership, getStaffIntegrity,
  getContinuitySettings, updateContinuitySettings,
} from "../api/resources";
import type { PermissionDef, Role, StaffMembership, StaffIntegritySummary, ContinuitySettings } from "../api/types";
import { extractErrorMessage } from "../lib/format";

export default function StaffPage() {
  const { branches } = useBusiness();
  const { hasPermission, isOwnerOrAdmin } = useAuth();
  const canManageStaff = hasPermission("manage_staff");
  const [view, setView] = useState<"staff" | "integrity" | "continuity">("staff");
  const [integrity, setIntegrity] = useState<StaffIntegritySummary | null>(null);
  const [integrityLoading, setIntegrityLoading] = useState(false);
  const [continuity, setContinuity] = useState<ContinuitySettings | null>(null);
  const [continuityLoading, setContinuityLoading] = useState(false);
  const [continuitySaving, setContinuitySaving] = useState(false);
  const [continuityError, setContinuityError] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<PermissionDef[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [members, setMembers] = useState<StaffMembership[]>([]);
  const [loading, setLoading] = useState(true);

  const [showRoleModal, setShowRoleModal] = useState(false);
  const [roleName, setRoleName] = useState("");
  const [roleError, setRoleError] = useState<string | null>(null);
  const [roleSubmitting, setRoleSubmitting] = useState(false);

  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set());
  const [permError, setPermError] = useState<string | null>(null);
  const [permSubmitting, setPermSubmitting] = useState(false);

  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("");
  const [inviteBranch, setInviteBranch] = useState("");
  const [inviteMode, setInviteMode] = useState<"create" | "existing">("create");
  const [inviteName, setInviteName] = useState("");
  const [invitePassword, setInvitePassword] = useState("");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [inviteSubmitting, setInviteSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    Promise.allSettled([getPermissionCatalog(), getRoles(), getMemberships()]).then(([p, r, m]) => {
      if (p.status === "fulfilled") setPermissions(p.value); else console.error("Failed to load permissions:", p.reason);
      if (r.status === "fulfilled") setRoles(r.value); else console.error("Failed to load roles:", r.reason);
      if (m.status === "fulfilled") setMembers(m.value); else console.error("Failed to load memberships:", m.reason);
    }).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  useEffect(() => {
    if (view !== "integrity" || !isOwnerOrAdmin()) return;
    setIntegrityLoading(true);
    getStaffIntegrity().then(setIntegrity).finally(() => setIntegrityLoading(false));
  }, [view]);

  useEffect(() => {
    if (view !== "continuity" || !isOwnerOrAdmin()) return;
    setContinuityLoading(true);
    getContinuitySettings().then(setContinuity).finally(() => setContinuityLoading(false));
  }, [view]);

  async function handleSaveContinuity(patch: Partial<ContinuitySettings>) {
    setContinuitySaving(true);
    setContinuityError(null);
    try {
      const updated = await updateContinuitySettings(patch);
      setContinuity(updated);
    } catch (err: any) {
      setContinuityError(extractErrorMessage(err, "Couldn't save that."));
    } finally {
      setContinuitySaving(false);
    }
  }

  async function handleCreateRole() {
    if (!roleName) { setRoleError("Give the role a name."); return; }
    setRoleSubmitting(true); setRoleError(null);
    try {
      await createRole({ name: roleName });
      setShowRoleModal(false);
      setRoleName("");
      refresh();
    } catch (err: any) {
      setRoleError(extractErrorMessage(err, "Couldn't create the role."));
    } finally { setRoleSubmitting(false); }
  }

  function openPermissionsEditor(role: Role) {
    setEditingRole(role);
    setSelectedCodes(new Set(role.permission_codes));
    setPermError(null);
  }

  function togglePermission(code: string) {
    setSelectedCodes((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code); else next.add(code);
      return next;
    });
  }

  async function handleSavePermissions() {
    if (!editingRole) return;
    setPermSubmitting(true); setPermError(null);
    try {
      await setRolePermissions(editingRole.id, Array.from(selectedCodes));
      setEditingRole(null);
      refresh();
    } catch (err: any) {
      setPermError(extractErrorMessage(err, "Couldn't save permissions."));
    } finally { setPermSubmitting(false); }
  }

  async function handleInvite() {
    if (!inviteEmail || !inviteRole) { setInviteError("Email and role are required."); return; }
    if (inviteMode === "create" && invitePassword.length < 8) { setInviteError("Set a password of at least 8 characters for this new login."); return; }
    setInviteSubmitting(true); setInviteError(null);
    try {
      const [firstName, ...rest] = inviteName.trim().split(" ");
      await inviteStaff({
        email: inviteEmail, role: inviteRole, branch: inviteBranch || null,
        ...(inviteMode === "create" ? { password: invitePassword, first_name: firstName || "", last_name: rest.join(" ") } : {}),
      });
      setShowInvite(false);
      setInviteEmail(""); setInviteRole(""); setInviteBranch(""); setInviteName(""); setInvitePassword("");
      refresh();
    } catch (err: any) {
      setInviteError(extractErrorMessage(err, "Couldn't add that person."));
    } finally { setInviteSubmitting(false); }
  }

  async function handleRevoke(m: StaffMembership) {
    if (!window.confirm(`Revoke access for ${m.user_email}?`)) return;
    await updateMembership(m.id, { is_active: false });
    refresh();
  }

  async function handleReactivate(m: StaffMembership) {
    await updateMembership(m.id, { is_active: true });
    refresh();
  }

  const permissionsByCategory = permissions.reduce<Record<string, PermissionDef[]>>((acc, p) => {
    (acc[p.category] ||= []).push(p);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader
        title="Staff & Roles"
        subtitle="Who can do what. New staff need a Truvanta account already — add them here once they've registered."
        actions={canManageStaff ? <button className="btn btn-primary" onClick={() => setShowInvite(true)}>Add staff</button> : undefined}
      />

      {isOwnerOrAdmin() && (
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button className={`btn ${view === "staff" ? "btn-primary" : "btn-ghost"}`} onClick={() => setView("staff")}>Staff & Roles</button>
          <button className={`btn ${view === "integrity" ? "btn-primary" : "btn-ghost"}`} onClick={() => setView("integrity")}>Staff Integrity</button>
          <button className={`btn ${view === "continuity" ? "btn-primary" : "btn-ghost"}`} onClick={() => setView("continuity")}>Business Continuity</button>
        </div>
      )}

      {view === "integrity" ? (
        <div className="card" style={{ padding: 24 }}>
          <h2 className="section-title" style={{ marginBottom: 4 }}>Staff Integrity</h2>
          <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 16 }}>
            Private to owners and admins. Compares each person's rate of discounts, returns, cancellations,
            stock adjustments, and credit changes against the business's own average — not a punishment
            score, just a signal worth a conversation if something looks off. Needs at least{" "}
            {integrity?.minimum_sales_for_rating ?? 15} sales processed before a rate is shown.
          </p>
          {integrityLoading ? (
            <div className="loading-row">Loading…</div>
          ) : !integrity || integrity.staff.length === 0 ? (
            <EmptyState title="No staff activity yet" />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Staff member</th><th className="num">Sales processed</th>
                  <th className="num">Exceptions</th><th className="num">Rate / 100 sales</th>
                  <th className="num">Avg. cash variance</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {integrity.staff.map((row) => (
                  <tr key={row.user_id}>
                    <td>{row.user_name}</td>
                    <td className="num">{row.sales_count}</td>
                    <td className="num">{row.exceptions_count}</td>
                    <td className="num">{row.exception_rate_per_100_sales ?? "—"}</td>
                    <td className="num">{row.avg_absolute_cash_variance ? Number(row.avg_absolute_cash_variance).toFixed(2) : "—"}</td>
                    <td>
                      <span className={`badge badge--${row.category === "above_average" ? "attention" : row.category === "typical" ? "good" : "neutral"}`}>
                        {row.category === "above_average" ? "Above average" : row.category === "typical" ? "Typical" : "Not enough data"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {integrity?.business_average_exception_rate_per_100_sales != null && (
            <p style={{ fontSize: 14, color: "var(--ink-300)", marginTop: 12 }}>
              Business average: {integrity.business_average_exception_rate_per_100_sales} exceptions per 100 sales.
            </p>
          )}
        </div>
      ) : view === "continuity" ? (
        <div className="card" style={{ padding: 24, maxWidth: 560 }}>
          <h2 className="section-title" style={{ marginBottom: 4 }}>Business Continuity Mode</h2>
          <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginBottom: 16 }}>
            If no owner logs in for a stretch of time, a backup manager you choose gets temporary
            owner-level access automatically — so an urgent approval, staff issue, or expense doesn't
            just sit stuck. It reverts the moment an owner logs back in, and every activation is
            recorded in the Activity Log.
          </p>
          {continuityLoading || !continuity ? (
            <div className="loading-row">Loading…</div>
          ) : (
            <>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15.5, marginBottom: 16, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={continuity.is_enabled}
                  onChange={(e) => handleSaveContinuity({ is_enabled: e.target.checked })}
                  disabled={continuitySaving}
                />
                Enable Business Continuity Mode
              </label>

              {continuity.is_enabled && (
                <>
                  <Field label="Backup manager">
                    <select
                      className="input"
                      value={continuity.backup_manager || ""}
                      onChange={(e) => handleSaveContinuity({ backup_manager: e.target.value || null })}
                      disabled={continuitySaving}
                    >
                      <option value="">Select a staff member…</option>
                      {members.map((m) => <option key={m.id} value={m.user}>{m.user_email}</option>)}
                    </select>
                  </Field>
                  <Field label="Inactivity threshold (days)" hint="If every owner is inactive this long, continuity mode activates">
                    <input
                      className="input"
                      type="number"
                      min={3}
                      value={continuity.inactivity_threshold_days}
                      onChange={(e) => handleSaveContinuity({ inactivity_threshold_days: parseInt(e.target.value, 10) || 14 })}
                      disabled={continuitySaving}
                    />
                  </Field>
                </>
              )}
              {continuityError && <p className="inline-error">{continuityError}</p>}
            </>
          )}
        </div>
      ) : (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <h2 className="section-title" style={{ margin: 0 }}>Roles</h2>
            {canManageStaff && <button className="btn btn-ghost" onClick={() => setShowRoleModal(true)}>+ New role</button>}
          </div>
          {loading ? <div className="loading-row">Loading…</div> : roles.length === 0 ? (
            <EmptyState title="No roles yet" />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {roles.map((r) => (
                <div key={r.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--paper-100)" }}>
                  <div>
                    <strong style={{ fontSize: 15.5 }}>{r.name}</strong>
                    <div style={{ fontSize: 13.5, color: "var(--ink-300)" }}>{r.permission_codes.length} permission(s)</div>
                  </div>
                  {canManageStaff && r.system_role !== "owner" && <button className="btn btn-ghost" onClick={() => openPermissionsEditor(r)}>Edit permissions</button>}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card" style={{ padding: 24 }}>
          <h2 className="section-title">Staff members</h2>
          {loading ? <div className="loading-row">Loading…</div> : members.length === 0 ? (
            <EmptyState title="No staff yet" />
          ) : (
            <table className="data-table">
              <thead><tr><th>Email</th><th>Role</th><th>Branch</th><th></th></tr></thead>
              <tbody>
                {members.map((m) => (
                  <tr key={m.id}>
                    <td>{m.user_email}</td>
                    <td>{m.role_name}</td>
                    <td>{m.branch_name || "All branches"}</td>
                    <td>
                      {canManageStaff && m.role_name !== "Owner" && m.is_active && (
                        <button className="btn btn-ghost" onClick={() => handleRevoke(m)}>Revoke</button>
                      )}
                      {!m.is_active && (
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          <span className="badge badge--neutral">revoked</span>
                          {canManageStaff && <button className="btn btn-ghost" onClick={() => handleReactivate(m)}>Restore</button>}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      )}

      {showRoleModal && (
        <Modal title="New role" onClose={() => setShowRoleModal(false)}>
          <Field label="Role name" required hint="e.g. Senior Cashier, Store Manager">
            <input className="input" value={roleName} onChange={(e) => setRoleName(e.target.value)} />
          </Field>
          {roleError && <p className="inline-error">{roleError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleCreateRole} disabled={roleSubmitting}>
            {roleSubmitting ? "Creating…" : "Create role"}
          </button>
        </Modal>
      )}

      {editingRole && (
        <Modal title={`Permissions — ${editingRole.name}`} onClose={() => setEditingRole(null)}>
          {Object.entries(permissionsByCategory).map(([category, perms]) => (
            <div key={category} style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 13.5, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--ink-300)", marginBottom: 8 }}>{category}</p>
              {perms.map((p) => (
                <label key={p.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15.5, padding: "6px 0", cursor: "pointer" }}>
                  <input type="checkbox" checked={selectedCodes.has(p.code)} onChange={() => togglePermission(p.code)} />
                  {p.label}
                </label>
              ))}
            </div>
          ))}
          {permError && <p className="inline-error">{permError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleSavePermissions} disabled={permSubmitting}>
            {permSubmitting ? "Saving…" : "Save permissions"}
          </button>
        </Modal>
      )}

      {showInvite && (
        <Modal title="Add staff member" onClose={() => setShowInvite(false)}>
          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            <button
              className={`btn ${inviteMode === "create" ? "btn-primary" : "btn-ghost"}`}
              style={{ flex: 1 }}
              onClick={() => setInviteMode("create")}
            >
              Create a new login
            </button>
            <button
              className={`btn ${inviteMode === "existing" ? "btn-primary" : "btn-ghost"}`}
              style={{ flex: 1 }}
              onClick={() => setInviteMode("existing")}
            >
              Add existing account
            </button>
          </div>
          <p style={{ fontSize: 15, color: "var(--ink-600)", marginBottom: 16 }}>
            {inviteMode === "create"
              ? "Set an email and password yourself and hand them to whoever's running that branch — no need for them to register anything themselves."
              : "They already have their own Truvanta account (from any business) — this just adds it here with the role and branch you pick."}
          </p>
          <Field label="Email" required>
            <input className="input" type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="e.g. north-branch@yourbusiness.com" />
          </Field>
          {inviteMode === "create" && (
            <>
              <Field label="Name" hint="Optional — helps you tell staff apart later.">
                <input className="input" value={inviteName} onChange={(e) => setInviteName(e.target.value)} />
              </Field>
              <Field label="Password" required hint="At least 8 characters — write it down to hand over.">
                <input className="input" type="text" value={invitePassword} onChange={(e) => setInvitePassword(e.target.value)} />
              </Field>
            </>
          )}
          <Field label="Role" required>
            <select className="input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
              <option value="">Select…</option>
              {roles.filter((r) => r.system_role !== "owner").map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </Field>
          <Field label="Branch" hint="Leave blank for access to all branches">
            <select className="input" value={inviteBranch} onChange={(e) => setInviteBranch(e.target.value)}>
              <option value="">All branches</option>
              {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </Field>
          {inviteError && <p className="inline-error">{inviteError}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleInvite} disabled={inviteSubmitting}>
            {inviteSubmitting ? "Adding…" : inviteMode === "create" ? "Create login & add to team" : "Add to team"}
          </button>
        </Modal>
      )}
    </div>
  );
}
