from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0007_platformsettings_admin_pin"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="universal_color",
            field=models.CharField(
                default="#E3A635", max_length=7,
                help_text="The platform's default accent color — shown on the login screen and used by "
                           "any business that hasn't picked its own branding color yet. A business's own "
                           "color (Settings → Business branding) always takes priority over this once set.",
            ),
        ),
    ]
