import secrets
import string
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _generate_code(existing: set) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if code not in existing:
            existing.add(code)
            return code


def backfill_signup_codes(apps, schema_editor):
    Business = apps.get_model("tenants", "Business")
    existing = set(Business.objects.exclude(signup_code="").values_list("signup_code", flat=True))
    for business in Business.objects.filter(models.Q(signup_code__isnull=True) | models.Q(signup_code="")):
        business.signup_code = _generate_code(existing)
        business.save(update_fields=["signup_code"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0007_business_theme_color"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="signup_code",
            field=models.CharField(max_length=12, null=True, blank=True, db_index=True),
        ),
        migrations.RunPython(backfill_signup_codes, noop),
        migrations.AlterField(
            model_name="business",
            name="signup_code",
            field=models.CharField(
                max_length=12, unique=True, db_index=True,
                help_text="Given to staff so they can register their own location as a branch of this "
                           "business, pending your approval. Owner/admin can regenerate it any time, "
                           "which immediately invalidates the old code.",
            ),
        ),
        migrations.CreateModel(
            name="BranchJoinRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("branch_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending", max_length=10)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("business", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branch_join_requests", to="tenants.business")),
                ("created_branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="tenants.branch")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branch_join_requests", to=settings.AUTH_USER_MODEL)),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
