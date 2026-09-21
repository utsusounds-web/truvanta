# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying; if it
# reports drift, regenerate with `makemigrations products`.

import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_pricehistory'),
        ('tenants', '0006_branch_parent_branch'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='parent_product',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='variants', to='products.product',
                help_text="Set this to make the product a variant of another product (e.g. this row is "
                          "'Red / Large' under the parent 'T-Shirt'). Leave blank for a standalone product.",
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='variant_attributes',
            field=models.JSONField(
                blank=True, default=dict,
                help_text='Free-form attributes distinguishing this variant, e.g. {"color": "Red", "size": "Large"}.',
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='is_bundle',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='ProductBundleItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('quantity', models.DecimalField(
                    decimal_places=3, max_digits=14,
                    validators=[django.core.validators.MinValueValidator(0.001)],
                    help_text='How many of the component (in its base unit) one bundle sale consumes.',
                )),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products_productbundleitem_set', to='tenants.business')),
                ('bundle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bundle_items', to='products.product')),
                ('component', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='used_in_bundles', to='products.product')),
            ],
        ),
        migrations.AddConstraint(
            model_name='productbundleitem',
            constraint=models.UniqueConstraint(fields=('bundle', 'component'), name='products_productbundleitem_bundle_component_uniq'),
        ),
    ]
