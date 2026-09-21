import { Navigate, NavLink, Outlet } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import AdminPinGate from "../components/AdminPinGate";
import { changeAdminPin } from "../api/tenants";
import "./AdminLayout.css";

// This is Truvanta's own internal control panel (plans, features,
// subscriptions across every tenant) — not something a business owner
// ever sees. It intentionally does NOT reuse AppLayout: that sidebar
// is full of business-specific links (POS, Inventory, Staff...) that
// mean nothing here, and sharing it made the admin console feel like
// an afterthought bolted onto the tenant app instead of its own tool.
const ADMIN_NAV = [
  { to: "/admin/usage", label: "Usage" },
  { to: "/admin/plans", label: "Plans" },
  { to: "/admin/features", label: "Features" },
  { to: "/admin/subscriptions", label: "Subscriptions" },
  { to: "/admin/overrides", label: "Overrides" },
  { to: "/admin/broadcast", label: "Broadcast" },
  { to: "/admin/support", label: "Support Access" },
  { to: "/admin/audit", label: "Global Audit" },
  { to: "/admin/webhooks", label: "Webhooks" },
  { to: "/admin/purge", label: "Data Purge" },
  { to: "/admin/layout", label: "Feature Layout" },
];

export default function AdminLayout() {
  const { user, memberships, logout } = useAuth();
  const [changingPin, setChangingPin] = useState(false);
  const [newPin, setNewPin] = useState("");
  const [pinMessage, setPinMessage] = useState<string | null>(null);
  const [pinSubmitting, setPinSubmitting] = useState(false);

  // Guard at the shell level, not just inside AdminPage — a non-staff
  // user shouldn't even see the admin chrome flash before redirecting.
  if (!user?.is_staff) return <Navigate to="/dashboard" replace />;

  async function handleChangePin(e: React.FormEvent) {
    e.preventDefault();
    if (!/^\d{4,8}$/.test(newPin)) {
      setPinMessage("PIN must be 4-8 digits.");
      return;
    }
    setPinSubmitting(true);
    setPinMessage(null);
    try {
      await changeAdminPin(newPin);
      setPinMessage("PIN changed.");
      setNewPin("");
      setTimeout(() => { setChangingPin(false); setPinMessage(null); }, 1200);
    } catch {
      setPinMessage("Couldn't change PIN.");
    } finally {
      setPinSubmitting(false);
    }
  }

  return (
    <AdminPinGate>
      <div className="admin-shell">
        <aside className="admin-sidebar">
          <div className="admin-mark">
            <span className="admin-mark-badge">ADMIN</span>
            TRUVANTA
          </div>
          <nav className="admin-nav">
            {ADMIN_NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `admin-nav-item ${isActive ? "admin-nav-item--active" : ""}`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="admin-sidebar-footer">
            {/* Most admin accounts are platform-staff-only and have no
                business membership to "exit" to — showing this link to
                them would be a dead end, landing on an empty dashboard. */}
            {memberships.length > 0 && (
              <NavLink to="/dashboard" className="admin-exit-link">← Exit to my business</NavLink>
            )}
            <span className="admin-user">{user?.email}</span>
            {changingPin ? (
              <form onSubmit={handleChangePin} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <input
                  className="input"
                  type="password"
                  inputMode="numeric"
                  placeholder="New PIN"
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ""))}
                  style={{ fontSize: 15 }}
                  autoFocus
                />
                {pinMessage && <span style={{ fontSize: 13, color: "var(--gold-500)" }}>{pinMessage}</span>}
                <div style={{ display: "flex", gap: 6 }}>
                  <button className="btn btn-primary" type="submit" disabled={pinSubmitting} style={{ flex: 1, fontSize: 14 }}>
                    {pinSubmitting ? "…" : "Save"}
                  </button>
                  <button type="button" className="btn btn-ghost" style={{ flex: 1, fontSize: 14 }} onClick={() => { setChangingPin(false); setPinMessage(null); }}>
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <button className="btn btn-ghost" onClick={() => setChangingPin(true)} style={{ fontSize: 14.5 }}>
                Change admin PIN
              </button>
            )}
            <button className="btn btn-ghost" onClick={logout}>Sign out</button>
          </div>
        </aside>
        <div className="admin-main">
          <Outlet />
        </div>
      </div>
    </AdminPinGate>
  );
}
