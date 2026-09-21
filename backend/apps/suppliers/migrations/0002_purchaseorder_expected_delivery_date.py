# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suppliers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorder',
            name='expected_delivery_date',
            field=models.DateField(
                blank=True, null=True,
                help_text="What the supplier promised, if given — powers the on-time % in the Supplier "
                          "Reliability Scorecard. Left blank, this PO simply isn't counted in that metric "
                          "rather than guessed at.",
            ),
        ),
    ]
