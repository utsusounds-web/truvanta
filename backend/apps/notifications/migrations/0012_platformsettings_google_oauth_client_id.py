from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0011_notification_is_read"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="google_oauth_client_id",
            field=models.CharField(
                blank=True, default="", max_length=255,
                help_text="From Google Cloud Console (APIs & Services > Credentials > OAuth 2.0 Client "
                           "ID, type 'Web application'). Not a secret — this is meant to be visible in "
                           "frontend JS, unlike the values above. Leave blank to keep 'Sign in with "
                           "Google' hidden on the login screen.",
            ),
        ),
    ]
