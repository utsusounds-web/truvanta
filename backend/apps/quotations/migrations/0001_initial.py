# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying; if it
# reports drift, regenerate with `makemigrations quotations`.

import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0006_branch_parent_branch'),
        ('customers', '0001_initial'),
        ('products', '0003_variants_and_bundles'),
        ('sales', '0006_paymentmethod'),
    ]

    operations = [
        migrations.CreateModel(
            name='Quotation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('document_type', models.CharField(choices=[('quotation', 'Quotation'), ('proforma_invoice', 'Proforma Invoice')], default='quotation', max_length=20)),
                ('reference_number', models.CharField(max_length=50)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('sent', 'Sent'), ('accepted', 'Accepted'), ('expired', 'Expired'), ('converted', 'Converted to Sale'), ('void', 'Void')], default='draft', max_length=20)),
                ('valid_until', models.DateField(blank=True, null=True)),
                ('notes', models.CharField(blank=True, max_length=500)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='quotations_quotation_set', to='tenants.business')),
                ('branch', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='quotations', to='tenants.branch')),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quotations', to='customers.customer')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.user')),
                ('converted_sale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='originating_quotation', to='sales.sale')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddConstraint(
            model_name='quotation',
            constraint=models.UniqueConstraint(fields=('business', 'reference_number'), name='quotations_quotation_business_reference_uniq'),
        ),
        migrations.CreateModel(
            name='QuotationItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0.001)])),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='quotations_quotationitem_set', to='tenants.business')),
                ('quotation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='quotations.quotation')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='products.product')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='products.unitofmeasure')),
            ],
        ),
    ]
