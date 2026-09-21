"""Canonical list of every feature that can be moved between dashboards,
and which hub each one lives under by default. This is the source of
truth the backend validates admin changes against; the frontend keeps
its own copy of the display details (title, description, icon, route)
that must reference these same keys.

Adding a genuinely new page later means adding it here AND in the
frontend's FEATURE_CATALOG (src/lib/featureCatalog.ts) — the two are
kept in sync by hand, not generated from one file, since one lives in
Python and the other in TypeScript.
"""

HUB_KEYS = {"sell_buy", "security", "business_health"}

DEFAULT_FEATURE_HUBS = {
    # Sell & Buy
    "pos": "sell_buy",
    "customers": "sell_buy",
    "quotations": "sell_buy",
    "returns": "sell_buy",
    "receipt_history": "sell_buy",
    "shifts": "sell_buy",
    "products": "sell_buy",
    "inventory": "sell_buy",
    "quick_audit": "sell_buy",
    "transfers": "sell_buy",
    "suppliers": "sell_buy",
    "purchase_orders": "sell_buy",
    # Security
    "staff": "security",
    "activity_log": "security",
    "staff_sessions": "security",
    "support_access": "security",
    "reconciliation": "security",
    "branches": "security",
    "account_security": "security",
    # Business Health
    "expenses": "business_health",
    "reports": "business_health",
    "statements": "business_health",
    "ledger": "business_health",
    "opening_balance": "business_health",
}


def resolve_feature_hubs(overrides: dict) -> dict:
    """Merge admin overrides over the defaults, dropping any override
    that references a feature key or hub that no longer exists —
    stale overrides (e.g. from a feature that was later removed)
    should never crash this, just get silently ignored."""
    resolved = dict(DEFAULT_FEATURE_HUBS)
    for feature_key, hub_key in (overrides or {}).items():
        if feature_key in DEFAULT_FEATURE_HUBS and hub_key in HUB_KEYS:
            resolved[feature_key] = hub_key
    return resolved
