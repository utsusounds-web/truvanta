import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useBusiness } from "../context/BusinessContext";
import { getUnreadNotificationCount } from "../api/resources";
import SyncStatusIndicator from "../components/SyncStatusIndicator";
import LoadingScreen from "../components/LoadingScreen";
import GlobalSearch from "../components/GlobalSearch";
import "./AppLayout.css";

const NAV_SECTIONS: { label: string; items: { to: string; label: string; icon: string; ownerOnly?: boolean }[] }[] = [
  {
    label: "",
    items: [{ to: "/dashboard", label: "Dashboard", icon: "◆" }],
  },
  {
    label: "",
    items: [
      { to: "/sell-buy", label: "Sell & Buy", icon: "🛒" },
      { to: "/security", label: "Security", icon: "🔒" },
      { to: "/business-health", label: "Business Health", icon: "📈" },
    ],
  },
  {
    label: "More",
    items: [
      { to: "/notifications", label: "Notifications", icon: "◈" },
      { to: "/documents", label: "Documents", icon: "▢" },
      { to: "/billing", label: "Billing", icon: "◈", ownerOnly: true },
      { to: "/help", label: "Help", icon: "◍" },
      { to: "/settings", label: "Settings", icon: "◍" },
    ],
  },
];

export default function AppLayout() {
  const { user, logout, isOwnerOrAdmin } = useAuth();
  const { branches, activeBranchId, setActiveBranchId, businessLogoUrl, businessName, loading } = useBusiness();
  // Persisted so the choice sticks across visits, not just this tab.
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("sbos_sidebar_collapsed") === "1");
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    function poll() {
      getUnreadNotificationCount().then((count) => { if (!cancelled) setUnreadCount(count); }).catch(() => {});
    }
    poll();
    // A minute is frequent enough to feel "live" for a low-volume
    // notification stream without hammering the server on every
    // single page navigation the way a fetch-on-route-change would.
    const interval = setInterval(poll, 60000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  function toggleCollapsed() {
    setCollapsed((c) => {
      localStorage.setItem("sbos_sidebar_collapsed", !c ? "1" : "0");
      return !c;
    });
  }

  // First load after login: branches (and the business profile) are
  // still being fetched, so there's nothing real to show yet — the
  // branded loading screen fills that gap instead of a blank shell.
  if (loading && branches.length === 0) {
    return <LoadingScreen logoUrl={businessLogoUrl} label="Loading your business…" />;
  }

  return (
    <div className={`app-shell ${collapsed ? "app-shell--collapsed" : ""}`}>
      <aside className="app-sidebar">
        <div className="app-mark">
          {businessLogoUrl ? (
            <img src={businessLogoUrl} alt={businessName || "Business logo"} className="app-mark-logo" />
          ) : (
            !collapsed && "TRUVANTA"
          )}
        </div>
        <button
          className="app-sidebar-toggle"
          onClick={toggleCollapsed}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar for a full-screen view"}
        >
          {collapsed ? "»" : "«"}
        </button>
        <nav className="app-nav">
          {NAV_SECTIONS.map((section, si) => (
            <div key={si} className="app-nav-section">
              {section.label && !collapsed && <div className="app-nav-label">{section.label}</div>}
              {section.items.filter((item) => !item.ownerOnly || isOwnerOrAdmin()).map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `app-nav-item ${isActive ? "app-nav-item--active" : ""}`}
                  title={collapsed ? item.label : undefined}
                >
                  <span className="app-nav-icon" style={{ position: "relative" }}>
                    {item.icon}
                    {item.to === "/notifications" && unreadCount > 0 && (
                      <span className="app-nav-badge" title={`${unreadCount} unread`} />
                    )}
                  </span>
                  {!collapsed && item.label}
                  {!collapsed && item.to === "/notifications" && unreadCount > 0 && (
                    <span className="app-nav-badge-count">{unreadCount > 99 ? "99+" : unreadCount}</span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="app-sidebar-footer">
          <NavLink to="/profile" className="app-user-row" title={collapsed ? user?.email : undefined}>
            {user?.profile_photo ? (
              <img src={user.profile_photo} alt="" className="app-user-avatar" />
            ) : (
              <span className="app-user-avatar app-user-avatar--placeholder">{user?.email?.[0]?.toUpperCase()}</span>
            )}
            {!collapsed && <span className="app-user">{user?.email}</span>}
          </NavLink>
          <button className="btn btn-ghost" onClick={logout} title={collapsed ? "Sign out" : undefined}>
            {collapsed ? "⏻" : "Sign out"}
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          {branches.length > 0 && (
            <select
              className="input branch-select"
              value={activeBranchId || ""}
              onChange={(e) => setActiveBranchId(e.target.value)}
            >
              {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          )}
          <div style={{ flex: 1 }} />
          <GlobalSearch />
          <div style={{ width: 16 }} />
          <SyncStatusIndicator />
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
