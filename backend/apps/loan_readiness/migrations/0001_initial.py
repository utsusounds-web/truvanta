# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying; if it
# reports drift, regenerate with `makemigrations loan_readiness`.

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0006_branch_parent_branch'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoanReadinessReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('period_start', models.DateField()),
                ('period_end', models.DateField()),
                ('snapshot_json', models.JSONField(help_text='Every figure printed on the report, frozen at generation time.')),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='loan_readiness_loanreadinessreport_set', to='tenants.business')),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
