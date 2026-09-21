// Single source of truth for every feature that can be moved between
// dashboards, and the display details (title, description, icon,
// route) for each. The `key` values here MUST exactly match
// DEFAULT_FEATURE_HUBS in backend/apps/notifications/feature_catalog.py —
// that file validates admin changes against these same keys, so a
// typo here means "unknown feature" errors from the API, not a
// silent mismatch.
//
// `visibleTo` is optional: when set, the tile only renders for users
// where that check passes (ownerOrAdmin, or a named permission) —
// unrelated to which hub it lives under.

export type HubKey = "sell_buy" | "security" | "business_health";

export interface FeatureCatalogEntry {
  key: string;
  title: string;
  description: string;
  icon: string;
  path: string;
  defaultHub: HubKey;
  group: string; // sub-heading shown when the feature is in its default hub
  visibleTo?: "ownerOrAdmin" | "view_profit";
}

export const FEATURE_CATALOG: FeatureCatalogEntry[] = [
  // --- Sell & Buy (default) ---
  { key: "pos", title: "Point of Sale", description: "Ring up a sale and print the receipt.", icon: "🛒", path: "/pos", defaultHub: "sell_buy", group: "Selling" },
  { key: "customers", title: "Customers", description: "Who owes you money, and debt aging.", icon: "👤", path: "/customers", defaultHub: "sell_buy", group: "Selling" },
  { key: "quotations", title: "Quotations", description: "Give a customer a price before they commit.", icon: "📋", path: "/quotations", defaultHub: "sell_buy", group: "Selling" },
  { key: "returns", title: "Returns", description: "Process a return, refund, or exchange.", icon: "↩️", path: "/returns", defaultHub: "sell_buy", group: "Selling" },
  { key: "receipt_history", title: "Receipt History", description: "Look up and reprint any past receipt.", icon: "🧾", path: "/receipt-history", defaultHub: "sell_buy", group: "Selling" },
  { key: "shifts", title: "Shifts", description: "Open and close a cash-handling shift.", icon: "🕐", path: "/shifts", defaultHub: "sell_buy", group: "Selling" },
  { key: "products", title: "Products", description: "Add products, set prices, manage variants.", icon: "📦", path: "/products", defaultHub: "sell_buy", group: "Stock" },
  { key: "inventory", title: "Inventory", description: "See stock levels and record movements.", icon: "📊", path: "/inventory", defaultHub: "sell_buy", group: "Stock" },
  { key: "quick_audit", title: "Quick Audit", description: "Spot-check stock counts are correct.", icon: "🔍", path: "/quick-audit", defaultHub: "sell_buy", group: "Stock" },
  { key: "transfers", title: "Transfers", description: "Move stock between branches.", icon: "🔄", path: "/transfers", defaultHub: "sell_buy", group: "Stock" },
  { key: "suppliers", title: "Suppliers", description: "Manage who you buy from and what you owe them.", icon: "🏭", path: "/suppliers", defaultHub: "sell_buy", group: "Buying" },
  { key: "purchase_orders", title: "Purchase Orders", description: "Order stock and record what actually arrives.", icon: "📥", path: "/purchase-orders", defaultHub: "sell_buy", group: "Buying" },

  // --- Security (default) ---
  { key: "staff", title: "Staff & Roles", description: "Who works here and what they're allowed to do.", icon: "👥", path: "/staff", defaultHub: "security", group: "Access & activity" },
  { key: "activity_log", title: "Activity Log", description: "Every sensitive action taken, with who and when.", icon: "📜", path: "/activity-log", defaultHub: "security", group: "Access & activity", visibleTo: "ownerOrAdmin" },
  { key: "staff_sessions", title: "Staff Sessions", description: "See when each branch/staff member logged in, from what device, and sign any of them out.", icon: "💻", path: "/staff-sessions", defaultHub: "security", group: "Access & activity", visibleTo: "ownerOrAdmin" },
  { key: "support_access", title: "Platform Support Access", description: "Grant Truvanta staff a time-limited login to help with support — you control when, for how long, and can revoke instantly.", icon: "🛟", path: "/support-access", defaultHub: "security", group: "Access & activity", visibleTo: "ownerOrAdmin" },
  { key: "reconciliation", title: "Cash Reconciliation", description: "Match payments received against what's expected.", icon: "✅", path: "/reconciliation", defaultHub: "security", group: "Access & activity" },
  { key: "branches", title: "Branches", description: "Manage your locations and who works where.", icon: "🏢", path: "/branches", defaultHub: "security", group: "Access & activity" },
  { key: "account_security", title: "Account Security", description: "Password, two-factor login, active sessions, duress password.", icon: "🔒", path: "/profile", defaultHub: "security", group: "Your account" },

  // --- Business Health (default) ---
  { key: "expenses", title: "Expenses", description: "Track and approve what's going out.", icon: "💸", path: "/expenses", defaultHub: "business_health", group: "Money going out" },
  { key: "reports", title: "Reports", description: "Sales, profit, and where your money went.", icon: "📈", path: "/reports", defaultHub: "business_health", group: "Reports & records", visibleTo: "view_profit" },
  { key: "statements", title: "Statements", description: "Downloadable statements — including loan readiness and cash-flow forecast.", icon: "📄", path: "/statements", defaultHub: "business_health", group: "Reports & records", visibleTo: "view_profit" },
  { key: "ledger", title: "Ledger", description: "The formal double-entry record behind every transaction.", icon: "📚", path: "/ledger", defaultHub: "business_health", group: "Reports & records", visibleTo: "view_profit" },
  { key: "opening_balance", title: "Opening Balance", description: "What your business had and owed when you started using Truvanta.", icon: "🏁", path: "/opening-balance", defaultHub: "business_health", group: "Reports & records", visibleTo: "ownerOrAdmin" },
];

export const HUB_TITLES: Record<HubKey, string> = {
  sell_buy: "Sell & Buy",
  security: "Security",
  business_health: "Business Health",
};
