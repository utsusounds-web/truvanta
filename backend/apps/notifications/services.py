"""Notification delivery over WhatsApp (Meta Cloud API) and email
(Gmail SMTP, via Django's normal email backend). Both are safe no-ops
when not configured — the Notification row is still created so the
in-app history is complete, and the attempt is recorded with a clear
'not configured' error rather than crashing the caller.

Credentials are resolved from PlatformSettings first (editable by
staff via the API/frontend, no redeploy needed) and fall back to the
.env values in settings.py so a fresh install still works until
someone sets them through the UI.
"""
import logging

import requests
from django.conf import settings
from django.core.mail import get_connection, send_mail

from .models import Notification, PlatformSettings

logger = logging.getLogger(__name__)


def _send_whatsapp(to_number: str, message: str) -> tuple[bool, str]:
    platform = PlatformSettings.load()
    token = platform.whatsapp_access_token or getattr(settings, "WHATSAPP_ACCESS_TOKEN", "")
    phone_number_id = platform.whatsapp_phone_number_id or getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")
    if not token or not phone_number_id:
        return False, "WhatsApp not configured (set it in Settings > Platform Integrations, or WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID in .env)."
    if not to_number:
        return False, "No WhatsApp number set for this business."
    try:
        resp = requests.post(
            f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": to_number.lstrip("+"),
                "type": "text",
                "text": {"body": message},
            },
            timeout=10,
        )
        if resp.status_code >= 400:
            return False, f"WhatsApp API error {resp.status_code}: {resp.text[:300]}"
        return True, ""
    except requests.RequestException as e:
        return False, f"WhatsApp request failed: {e}"


def _send_email(to_email: str, subject: str, message: str) -> tuple[bool, str]:
    platform = PlatformSettings.load()
    host_user = platform.email_host_user or getattr(settings, "EMAIL_HOST_USER", "")
    host_password = platform.email_host_password or getattr(settings, "EMAIL_HOST_PASSWORD", "")
    if not host_user:
        return False, "Email not configured (set it in Settings > Platform Integrations, or EMAIL_HOST_USER / EMAIL_HOST_PASSWORD in .env for Gmail SMTP)."
    if not to_email:
        return False, "No notification email set for this business."
    try:
        connection = get_connection(
            backend=settings.EMAIL_BACKEND, host=settings.EMAIL_HOST, port=settings.EMAIL_PORT,
            username=host_user, password=host_password, use_tls=settings.EMAIL_USE_TLS,
        )
        send_mail(subject, message, host_user, [to_email], fail_silently=False, connection=connection)
        return True, ""
    except Exception as e:  # noqa: BLE001 — deliberately broad: any SMTP failure should degrade to a logged error, not crash the caller
        return False, f"Email send failed: {e}"


def notify(*, business, level: str, title: str, message: str, branch=None, link_path: str = "") -> Notification:
    """Create the Notification record and attempt delivery on every
    channel the business has configured. Always returns the record,
    even if every channel fails — delivery failure is never silent,
    but it also never blocks the business event that triggered it.
    `link_path` is the in-app route this is about (e.g. '/inventory')
    so the notification can take the owner straight to it.
    """
    notification = Notification.objects.create(
        business=business, branch=branch, level=level, title=title, message=message, link_path=link_path,
    )

    whatsapp_number = business.notification_whatsapp_number
    if whatsapp_number:
        from apps.billing.services import business_has_feature
        if business_has_feature(business.id, "whatsapp_notifications"):
            notification.whatsapp_attempted = True
            delivered, error = _send_whatsapp(whatsapp_number, f"{title}\n\n{message}")
            notification.whatsapp_delivered = delivered
            notification.whatsapp_error = error
            if not delivered:
                logger.info("WhatsApp notification not delivered: %s", error)
        else:
            # Deliberately NOT marked as "attempted" — this isn't a
            # delivery failure, it's a plan limit. The in-app
            # notification (and email, if configured) still go out
            # either way; WhatsApp delivery is the paid convenience on
            # top, not the only way to be told.
            notification.whatsapp_error = "WhatsApp alerts aren't included in your current plan."

    email = business.notification_email or business.email
    if email:
        notification.email_attempted = True
        delivered, error = _send_email(email, f"[Truvanta] {title}", message)
        notification.email_delivered = delivered
        notification.email_error = error
        if not delivered:
            logger.info("Email notification not delivered: %s", error)

    notification.save()
    return notification
