from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0008_business_signup_code_branchjoinrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="support_access_expires_at",
            field=models.DateTimeField(
                blank=True, null=True,
                help_text="While set and in the future, Truvanta platform staff may log into this "
                           "business to help with support — only ever with the owner/admin explicitly "
                           "granting it here first, for a limited time, and revocable instantly.",
            ),
        ),
    ]
