# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='billing_interval',
            field=models.CharField(
                choices=[('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')],
                default='monthly', max_length=10,
            ),
        ),
    ]
