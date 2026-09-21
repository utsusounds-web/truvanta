from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0008_platformsettings_universal_color"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="minimum_client_version",
            field=models.CharField(
                blank=True, default="", max_length=20,
                help_text="If set, any frontend build older than this version is blocked behind a "
                           "full-screen 'please refresh' notice — for forcing everyone onto a build with "
                           "a critical fix (e.g. ledger math) before they can keep working. Leave blank to "
                           "never force a refresh. Format: e.g. '1.2.0'.",
            ),
        ),
    ]
