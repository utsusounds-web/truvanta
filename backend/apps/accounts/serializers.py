from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User, Role, Permission, Membership, UserSession


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name", "phone_number",
            "is_staff", "profile_photo", "two_factor_enabled",
        ]
        read_only_fields = ["id", "is_staff", "two_factor_enabled"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "first_name", "last_name", "phone_number"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        # The very first account on a fresh install automatically becomes
        # the platform admin (is_staff) — this is what makes the
        # "Platform Admin" sidebar link and page appear. Without this,
        # a fresh install has no admin at all until someone runs
        # `createsuperuser` from the command line, which most people
        # setting this up for the first time never think to do.
        # Every account after the first is a normal, non-staff account.
        if not User.objects.exists():
            user.is_staff = True
        user.save()
        return user


class RoleSerializer(serializers.ModelSerializer):
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "business", "name", "system_role", "description", "permission_codes"]
        read_only_fields = ["id", "business"]

    def get_permission_codes(self, obj):
        return list(obj.role_permissions.values_list("permission__code", flat=True))


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "label", "category"]
        read_only_fields = fields


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_system_role = serializers.CharField(source="role.system_role", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)
    permission_codes = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id", "user", "user_email", "business", "branch", "branch_name", "role", "role_name",
            "role_system_role", "permission_codes", "is_active", "joined_at",
        ]
        read_only_fields = ["id", "user", "business", "joined_at"]

    def get_permission_codes(self, obj):
        # Owner bypasses the granular system entirely (Membership.has_permission
        # short-circuits to True for it) — surface that as "every code" so the
        # frontend doesn't need to separately know about system_role == owner.
        if obj.role.system_role == "owner":
            return list(Permission.objects.values_list("code", flat=True))
        return list(obj.role.role_permissions.values_list("permission__code", flat=True))


class StaffInviteSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.UUIDField()
    branch = serializers.UUIDField(required=False, allow_null=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, validators=[validate_password])
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)


class UserSessionSerializer(serializers.ModelSerializer):
    expires_at = serializers.DateTimeField(source="outstanding_token.expires_at", read_only=True)

    class Meta:
        model = UserSession
        fields = ["id", "device_label", "ip_address", "created_at", "last_seen_at", "expires_at"]
        read_only_fields = fields


class BusinessStaffSessionSerializer(UserSessionSerializer):
    """Same session fields as UserSessionSerializer, plus who the
    session belongs to — needed here because an owner is looking at
    other people's sessions, not just their own device list."""
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.SerializerMethodField()

    class Meta(UserSessionSerializer.Meta):
        fields = UserSessionSerializer.Meta.fields + ["user_id", "user_email", "user_name"]
        read_only_fields = fields

    def get_user_name(self, obj):
        full_name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return full_name or obj.user.email
