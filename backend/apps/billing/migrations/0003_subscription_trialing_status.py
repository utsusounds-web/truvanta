# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_plan_weekly_interval'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=models.CharField(
                choices=[
                    ('none', 'No subscription'), ('trialing', 'Free trial'),
                    ('pending', 'Pending first payment'), ('active', 'Active'),
                    ('past_due', 'Payment failed / past due'), ('canceled', 'Canceled'),
                ],
                default='none', max_length=12,
            ),
        ),
    ]
