import apps.core.crypto
from django.db import migrations


class Migration(migrations.Migration):
    """Fixes a real bug: these fields were blank=True (form-level only)
    but had no database default, so the NOT NULL column rejected every
    new user row that didn't explicitly set them — which was every
    registration, since nothing sets a 2FA secret or duress password
    at signup time."""

    dependencies = [
        ('accounts', '0007_user_duress_password'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='two_factor_secret',
            field=apps.core.crypto.EncryptedCharField(
                blank=True, default="", max_length=500,
                help_text="TOTP secret, encrypted at rest. Blank until setup is confirmed (see accounts.views 2FA endpoints).",
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='duress_password_hash',
            field=apps.core.crypto.EncryptedCharField(
                blank=True, default="", max_length=500,
                help_text="Hashed duress password, encrypted at rest. Blank until the user sets one up in Security settings.",
            ),
        ),
    ]
