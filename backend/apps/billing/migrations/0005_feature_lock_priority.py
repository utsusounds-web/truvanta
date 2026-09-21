from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0004_plan_daily_interval"),
    ]

    operations = [
        migrations.AddField(
            model_name="feature",
            name="lock_priority",
            field=models.IntegerField(
                default=100,
                help_text="Lower locks first. When a trial or subscription lapses and a grace "
                           "period is configured (see PlatformSettings), only the lowest-numbered "
                           "features here stay usable during it — everything else locks "
                           "immediately. Purely an admin ordering knob; it has no effect while "
                           "rent mode is on or a plan/trial already grants the feature outright.",
            ),
        ),
    ]
