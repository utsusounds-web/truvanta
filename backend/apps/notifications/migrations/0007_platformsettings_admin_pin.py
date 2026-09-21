from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0006_fix_platformsettings_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="admin_pin_hash",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="admin_pin_set_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="admin_pin_failed_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="admin_pin_locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
