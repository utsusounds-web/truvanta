from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0004_encrypt_platform_secrets"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="link_path",
            field=models.CharField(
                blank=True, max_length=200,
                help_text="In-app route this notification is about, e.g. '/inventory' — lets the "
                           "frontend take the owner straight to the thing that needs attention.",
            ),
        ),
    ]
