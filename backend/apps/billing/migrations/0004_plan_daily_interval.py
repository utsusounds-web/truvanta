from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_subscription_trialing_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plan",
            name="billing_interval",
            field=models.CharField(
                choices=[
                    ("daily", "Daily"),
                    ("weekly", "Weekly"),
                    ("monthly", "Monthly"),
                    ("yearly", "Yearly"),
                ],
                default="monthly", max_length=10,
            ),
        ),
    ]
