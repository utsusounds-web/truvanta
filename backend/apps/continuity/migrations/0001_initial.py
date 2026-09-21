# NOTE: hand-written (no Django available in the review sandbox) — run
# `python manage.py makemigrations --check` before applying; if it
# reports drift, regenerate with `makemigrations continuity`.

import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenants', '0006_branch_parent_branch'),
        ('accounts', '0007_user_duress_password'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContinuitySettings',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_enabled', models.BooleanField(default=False)),
                ('inactivity_threshold_days', models.PositiveSmallIntegerField(
                    default=14, validators=[django.core.validators.MinValueValidator(3)],
                    help_text='If every owner has been inactive this many days, continuity mode activates.',
                )),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='continuity_continuitysettings_set', to='tenants.business')),
                ('backup_manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='continuity_backup_for', to='accounts.user')),
            ],
        ),
        migrations.AddConstraint(
            model_name='continuitysettings',
            constraint=models.UniqueConstraint(fields=('business',), name='one_continuity_settings_per_business'),
        ),
        migrations.CreateModel(
            name='ContinuityActivation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('activated_at', models.DateTimeField(auto_now_add=True)),
                ('deactivated_at', models.DateTimeField(blank=True, null=True)),
                ('deactivation_reason', models.CharField(blank=True, max_length=200)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='continuity_continuityactivation_set', to='tenants.business')),
                ('backup_manager', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='continuity_activations', to='accounts.user')),
            ],
            options={'ordering': ['-activated_at']},
        ),
    ]
