# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying.

import apps.core.crypto
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_user_two_factor'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='duress_password_hash',
            field=apps.core.crypto.EncryptedCharField(
                blank=True, max_length=500,
                help_text="Hashed duress password, encrypted at rest. Blank until the user sets one up in Security settings.",
            ),
        ),
    ]
