from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0012_platformsettings_google_oauth_client_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="trial_grace_days",
            field=models.IntegerField(
                default=0,
                help_text="After a trial or subscription lapses, how many days to keep a reduced "
                           "set of features working (see trial_grace_feature_count and "
                           "Feature.lock_priority) before locking everything down to just the "
                           "free core. 0 means lock everything immediately, the same as before "
                           "this setting existed.",
            ),
        ),
        migrations.AddField(
            model_name="platformsettings",
            name="trial_grace_feature_count",
            field=models.IntegerField(
                default=0,
                help_text="During the grace window above, how many features (ranked by lowest "
                           "lock_priority first) stay usable. E.g. 2 keeps only the two features "
                           "an admin has marked as least urgent to lock working; everything else "
                           "locks right away. Ignored when trial_grace_days is 0.",
            ),
        ),
    ]
