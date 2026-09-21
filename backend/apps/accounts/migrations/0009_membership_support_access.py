from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_fix_encrypted_field_defaults"),
    ]

    operations = [
        migrations.AddField(
            model_name="membership",
            name="is_support_access",
            field=models.BooleanField(
                default=False,
                help_text="Marks this as a temporary platform-support login, created only while the "
                           "business's owner/admin has an active support-access grant open. Automatically "
                           "stops working the moment that grant expires or is revoked — see "
                           "get_active_membership().",
            ),
        ),
    ]
