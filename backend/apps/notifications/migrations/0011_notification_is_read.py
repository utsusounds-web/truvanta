from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0010_platformsettings_feature_hub_overrides"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="is_read",
            field=models.BooleanField(
                default=False,
                help_text="Whether anyone at the business has opened/acknowledged this yet — "
                           "drives the unread indicator in the app, separate from delivery status "
                           "above (a notification can be delivered by WhatsApp and still unread here).",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="read_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
