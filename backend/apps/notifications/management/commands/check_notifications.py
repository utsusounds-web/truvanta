"""Run the periodic notification checks (overdue debts, daily summary,
subscription-expiry warnings) across every active business. Point a
cron job at this — e.g. hourly for overdue debts, once a day (evening)
for the daily summary and expiry warnings:

    0 * * * * cd /path/to/backend && python manage.py check_notifications --overdue-debts
    0 20 * * * cd /path/to/backend && python manage.py check_notifications --daily-summary --expiring-subscriptions

There's no in-process task queue (Celery) in this project — this
command is the intended way to schedule these until one is added.
"""
from django.core.management.base import BaseCommand

from apps.notifications import triggers
from apps.tenants.models import Business, Branch


class Command(BaseCommand):
    help = "Run periodic notification checks (overdue debts, daily sales summary, subscription-expiry warnings) for every active business."

    def add_arguments(self, parser):
        parser.add_argument("--overdue-debts", action="store_true", help="Check for overdue customer debts.")
        parser.add_argument("--daily-summary", action="store_true", help="Send a daily sales summary per branch.")
        parser.add_argument("--expiring-subscriptions", action="store_true", help="Warn businesses before their trial/subscription lapses.")
        parser.add_argument("--low-stock", action="store_true", help="Warn about products at or below their reorder level.")

    def handle(self, *args, **options):
        run_overdue = options["overdue_debts"]
        run_summary = options["daily_summary"]
        run_expiring = options["expiring_subscriptions"]
        run_low_stock = options["low_stock"]
        if not run_overdue and not run_summary and not run_expiring and not run_low_stock:
            run_overdue = run_summary = run_expiring = run_low_stock = True  # default: run all

        for business in Business.objects.filter(is_active=True):
            if run_overdue:
                result = triggers.check_overdue_debts(business)
                if result:
                    self.stdout.write(f"[{business.name}] overdue debt alert sent")
            if run_low_stock:
                result = triggers.check_low_stock(business)
                if result:
                    self.stdout.write(f"[{business.name}] low-stock alert sent")
            if run_summary:
                for branch in Branch.objects.filter(business=business, is_active=True):
                    triggers.send_daily_summary(business, branch)
                    self.stdout.write(f"[{business.name}] daily summary sent for {branch.name}")
            if run_expiring:
                result = triggers.check_expiring_subscriptions(business)
                if result:
                    self.stdout.write(f"[{business.name}] subscription-expiry warning sent")

        self.stdout.write(self.style.SUCCESS("Notification checks complete."))
