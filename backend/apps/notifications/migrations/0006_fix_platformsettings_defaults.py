import apps.core.crypto
from django.db import migrations


class Migration(migrations.Migration):
    """Fixes a real bug: PlatformSettings.load() creates its singleton
    row with only pk=1 set. These three fields were blank=True
    (form-level only) with no database default, so the NOT NULL
    column rejected that row — meaning the very first password-reset
    email, notification, or rent-mode check anywhere in the app would
    crash the whole request the first time PlatformSettings.load()
    ever ran."""

    dependencies = [
        ("notifications", "0005_notification_link_path"),
    ]

    operations = [
        migrations.AlterField(
            model_name="platformsettings",
            name="whatsapp_access_token",
            field=apps.core.crypto.EncryptedCharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="platformsettings",
            name="email_host_password",
            field=apps.core.crypto.EncryptedCharField(
                blank=True, default="", max_length=500,
                help_text="A Gmail App Password, not the account password. Encrypted at rest.",
            ),
        ),
        migrations.AlterField(
            model_name="platformsettings",
            name="platform_paystack_secret_key",
            field=apps.core.crypto.EncryptedCharField(blank=True, default="", max_length=500),
        ),
    ]
