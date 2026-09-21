from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0009_platformsettings_minimum_client_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="feature_hub_overrides",
            field=models.JSONField(
                blank=True, default=dict,
                help_text="Platform-admin overrides for which dashboard (Sell & Buy / Security / "
                           "Business Health) a feature currently lives under, keyed by feature key. "
                           "A feature not present here uses its built-in default hub. Applies to "
                           "every business — this is a layout decision, not a per-business setting.",
            ),
        ),
    ]
