# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying; if it
# reports drift, regenerate with `makemigrations sales`.

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0005_business_default_tax_rate_percent'),
        ('sales', '0005_exchangerate_payment_foreign_currency'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('code', models.SlugField(help_text="Stable identifier — 'cash' is reserved and can't be reused for a different method.", max_length=30)),
                ('name', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sales_paymentmethod_set', to='tenants.business')),
            ],
            options={
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='paymentmethod',
            constraint=models.UniqueConstraint(fields=('business', 'code'), name='unique_payment_method_code_per_business'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(max_length=30),
        ),
    ]
