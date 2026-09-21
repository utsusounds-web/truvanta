"""Grants Platform Admin access to an existing account, by email.

Use this if your account was created before the "first account becomes
admin automatically" behavior existed, or if you want to promote a
different existing account to platform admin later.

    python manage.py make_staff you@example.com

Safe to run anytime — only ever changes the one flag (is_staff) on the
one account you name; nothing else about the account or its data is touched.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant Platform Admin (is_staff) access to an existing account by email."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str)

    def handle(self, *args, **options):
        User = get_user_model()
        email = options["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"No account found with email '{email}'.")

        if user.is_staff:
            self.stdout.write(self.style.WARNING(f"{email} already has Platform Admin access."))
            return

        user.is_staff = True
        user.save(update_fields=["is_staff"])
        self.stdout.write(self.style.SUCCESS(
            f"Done. {email} now has Platform Admin access — sign out and back in, "
            f"and the 'Platform Admin' link will appear in the sidebar."
        ))
