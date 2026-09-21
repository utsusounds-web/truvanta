"""Seeds a starter catalog of gatable Features and example Plans so
the billing system has something usable immediately instead of an
empty admin panel. Safe to re-run — uses get_or_create throughout.
Edit prices/packaging afterwards from the admin panel; this is just a
sensible starting point, not a fixed pricing model.

    python manage.py seed_billing
"""
from django.core.management.base import BaseCommand

from apps.billing.models import Feature, Plan

FEATURES = [
    ("ai_addon", "AI Bookkeeping", "Voice bookkeeping, receipt scanning, 'ask my business'.", "AI"),
    ("multi_branch", "Multi-Branch", "More than one branch, plus inter-branch stock transfers.", "Operations"),
    ("advanced_reports", "Advanced Reports", "Profitability breakdowns, CSV export, deeper analytics.", "Reporting"),
    ("whatsapp_notifications", "WhatsApp Alerts", "Critical/important alerts delivered via WhatsApp.", "Notifications"),
    ("document_vault", "Document Vault", "Secure storage for business documents and files.", "Storage"),
    ("purchase_orders", "Purchase Orders", "Create and track purchase orders with suppliers.", "Operations"),
    ("away_mode", "Owner Away Mode", "Real-time alerts on discounts/refunds above your thresholds.", "Protection"),
    ("offline_sync", "Offline Sync", "Keep working with no internet; syncs automatically when back online.", "Operations"),
]

PLANS = [
    # (name, slug, price, currency, interval, sort_order, feature_keys)
    ("Starter", "starter", 5000, "NGN", "monthly", 1, ["advanced_reports", "document_vault"]),
    ("Pro", "pro", 15000, "NGN", "monthly", 2,
     ["advanced_reports", "document_vault", "multi_branch", "purchase_orders", "away_mode"]),
    ("Business", "business", 35000, "NGN", "monthly", 3,
     ["advanced_reports", "document_vault", "multi_branch", "purchase_orders",
      "away_mode", "ai_addon", "whatsapp_notifications", "offline_sync"]),
]


class Command(BaseCommand):
    help = "Seed default billing Features and starter Plans."

    def handle(self, *args, **options):
        feature_objs = {}
        for key, name, description, category in FEATURES:
            feature, created = Feature.objects.get_or_create(
                key=key, defaults={"name": name, "description": description, "category": category},
            )
            feature_objs[key] = feature
            self.stdout.write(f"{'Created' if created else 'Exists '} feature: {key}")

        for name, slug, price, currency, interval, sort_order, keys in PLANS:
            plan, created = Plan.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name, "price_amount": price, "currency": currency,
                    "billing_interval": interval, "sort_order": sort_order,
                },
            )
            plan.features.set([feature_objs[k] for k in keys])
            self.stdout.write(f"{'Created' if created else 'Exists '} plan: {name} ({len(keys)} features)")

        self.stdout.write(self.style.SUCCESS("Billing catalog seeded. Edit pricing/packaging from the admin panel."))
