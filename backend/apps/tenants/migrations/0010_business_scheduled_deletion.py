import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0009_business_support_access"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="business",
            name="pending_deletion_at",
            field=models.DateTimeField(
                blank=True, null=True,
                help_text="Once this passes, the business becomes eligible for permanent deletion — but "
                           "deletion still never happens automatically, staff must explicitly execute it.",
            ),
        ),
        migrations.AddField(
            model_name="business",
            name="deletion_requested_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="+", to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
