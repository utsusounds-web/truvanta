import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ledger", "0001_initial"),
        ("tenants", "0010_business_scheduled_deletion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OpeningBalanceStatement",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("as_of_date", models.DateField(help_text="The date this snapshot represents — usually 'today', but can be backdated to when the business actually started using Truvanta.")),
                ("cash_on_hand", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("bank_balance", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("accounts_receivable", models.DecimalField(decimal_places=2, default=0, help_text="Total money customers currently owe you.", max_digits=14)),
                ("inventory_value", models.DecimalField(decimal_places=2, default=0, help_text="What your current stock is worth at cost.", max_digits=14)),
                ("fixed_assets", models.DecimalField(decimal_places=2, default=0, help_text="Equipment, furniture, fittings — things you own that aren't for resale.", max_digits=14)),
                ("accounts_payable", models.DecimalField(decimal_places=2, default=0, help_text="Total you currently owe suppliers.", max_digits=14)),
                ("loans_payable", models.DecimalField(decimal_places=2, default=0, help_text="Outstanding loans or other debts.", max_digits=14)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("business", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="opening_balance", to="tenants.business")),
                ("journal_entry", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="ledger.journalentry")),
                ("recorded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
