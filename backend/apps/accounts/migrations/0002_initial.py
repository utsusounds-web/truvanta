import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('tenants', '0003_business_paystack_public_key_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('system_role', models.CharField(blank=True, choices=[('owner', 'Owner'), ('admin', 'Admin / Manager'), ('cashier', 'Sales Staff / Cashier'), ('inventory', 'Inventory Staff'), ('accountant', 'Accountant')], max_length=20)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='tenants.business')),
            ],
            options={
                'unique_together': {('business', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('is_active', models.BooleanField(default=True)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('branch', models.ForeignKey(blank=True, help_text='Leave blank for access to all branches of the business.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='tenants.branch')),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='tenants.business')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='memberships', to='accounts.role')),
            ],
            options={
                'unique_together': {('user', 'business', 'branch')},
            },
        ),
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.permission')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='accounts.role')),
            ],
            options={
                'unique_together': {('role', 'permission')},
            },
        ),
    ]
