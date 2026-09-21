from django.db import migrations

PERMISSIONS = [
    ("view_profit", "View profit figures", "financial"),
    ("delete_historical_transactions", "Delete/void completed transactions", "sales"),
    ("change_protected_prices", "Change protected product prices", "products"),
    ("access_confidential_profit_info", "Access confidential profit information", "financial"),
    ("modify_sensitive_records", "Modify sensitive records", "audit"),
    ("access_owner_only_information", "Access owner-only information", "financial"),
    ("approve_expenses", "Approve or reject expenses", "expenses"),
    ("approve_returns", "Approve returns and refunds", "returns"),
    ("give_large_discounts", "Give discounts above the configured limit", "sales"),
    ("manage_staff", "Manage staff, roles, and permissions", "accounts"),
    ("manage_products", "Add or edit products and pricing", "products"),
    ("manage_inventory", "Record stock adjustments and transfers", "inventory"),
    ("manage_suppliers", "Manage suppliers and purchase orders", "suppliers"),
    ("view_reports", "View reports and dashboards", "reports"),
    ("cancel_sales", "Cancel completed sales", "sales"),
]


def seed(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    for code, label, category in PERMISSIONS:
        Permission.objects.get_or_create(code=code, defaults={"label": label, "category": category})


def unseed(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(code__in=[p[0] for p in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_initial")]
    operations = [migrations.RunPython(seed, unseed)]
