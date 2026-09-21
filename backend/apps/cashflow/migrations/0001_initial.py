# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying; if it
# reports drift, regenerate with `makemigrations cashflow`.

import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0006_branch_parent_branch'),
        ('expenses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringExpenseSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text="e.g. 'Shop rent', 'Staff salaries'", max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('day_of_month', models.PositiveSmallIntegerField(
                    help_text='Day of the month this is due. For months shorter than this, treated as due on the last day.',
                    validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)],
                )),
                ('is_active', models.BooleanField(default=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='cashflow_recurringexpenseschedule_set', to='tenants.business')),
                ('branch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tenants.branch')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='expenses.expensecategory')),
            ],
            options={'ordering': ['day_of_month', 'name']},
        ),
    ]
