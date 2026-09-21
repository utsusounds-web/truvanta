"""Standard token-based password reset. Uses Django's own
PasswordResetTokenGenerator (same mechanism Django admin uses) —
time-limited, single-use-in-practice (invalidated by any password or
last_login change), no custom crypto to get wrong. The reset link
carries a base64-encoded user id + the token; both are required and
checked server-side, and the response never reveals whether an email
address has an account (prevents account enumeration).
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import get_connection, send_mail
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .models import User

token_generator = PasswordResetTokenGenerator()


def _resolve_email_credentials():
    from apps.notifications.models import PlatformSettings
    platform = PlatformSettings.load()
    host_user = platform.email_host_user or getattr(settings, "EMAIL_HOST_USER", "")
    host_password = platform.email_host_password or getattr(settings, "EMAIL_HOST_PASSWORD", "")
    return host_user, host_password


def request_password_reset(email: str) -> None:
    """Always succeeds from the caller's point of view (no account
    enumeration) — silently does nothing if the email isn't registered."""
    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"

    host_user, host_password = _resolve_email_credentials()
    if not host_user:
        return  # Email not configured yet — nothing to send to, nothing crashes.

    connection = get_connection(
        backend=settings.EMAIL_BACKEND, host=settings.EMAIL_HOST, port=settings.EMAIL_PORT,
        username=host_user, password=host_password, use_tls=settings.EMAIL_USE_TLS,
    )
    send_mail(
        "Reset your Truvanta password",
        f"Someone asked to reset the password on this account. If that was you, use this link "
        f"(valid for a limited time):\n\n{reset_url}\n\nIf you didn't request this, you can ignore this email.",
        host_user, [user.email], fail_silently=True, connection=connection,
    )


def confirm_password_reset(uidb64: str, token: str, new_password: str) -> tuple[bool, str]:
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return False, "This reset link is invalid."

    if not token_generator.check_token(user, token):
        return False, "This reset link is invalid or has expired — request a new one."

    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError
    try:
        validate_password(new_password, user=user)
    except ValidationError as e:
        return False, " ".join(e.messages)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    return True, ""
