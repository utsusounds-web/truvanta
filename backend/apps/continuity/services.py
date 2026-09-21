from django.utils import timezone

from apps.audit.services import log_action
from apps.notifications.services import notify


def check_and_apply_continuity(*, business):
    """Evaluates and applies Business Continuity Mode for one
    business. There's no background task runner in this deployment
    (see the app-level note on that), so this is designed to be
    called lazily and cheaply at the moments it actually matters —
    see continuity.views for exactly where it's hooked in — rather
    than needing a cron job. Safe to call as often as needed: it's
    idempotent (calling it when nothing has changed does nothing).
    """
    from .models import ContinuitySettings, ContinuityActivation
    from apps.accounts.models import Membership

    settings_row = ContinuitySettings.objects.filter(business=business).first()
    if not settings_row or not settings_row.is_enabled or not settings_row.backup_manager:
        return

    owner_memberships = Membership.objects.filter(
        business=business, role__system_role="owner", is_active=True,
    ).select_related("user")
    if not owner_memberships.exists():
        return  # nothing to compare against — leave it alone rather than guess

    now = timezone.now()
    threshold = timezone.timedelta(days=settings_row.inactivity_threshold_days)

    most_recent_owner_login = None
    for m in owner_memberships:
        if m.user.last_login and (most_recent_owner_login is None or m.user.last_login > most_recent_owner_login):
            most_recent_owner_login = m.user.last_login

    owner_overdue = most_recent_owner_login is None or (now - most_recent_owner_login) > threshold

    active_activation = ContinuityActivation.objects.filter(
        business=business, backup_manager=settings_row.backup_manager, deactivated_at__isnull=True,
    ).first()

    if owner_overdue and not active_activation:
        activation = ContinuityActivation.objects.create(business=business, backup_manager=settings_row.backup_manager)
        log_action(
            business=business, actor=None, action="permission_change", target=activation,
            new_value={"backup_manager": str(settings_row.backup_manager_id), "reason": "owner inactivity threshold reached"},
            reason=f"Business Continuity Mode activated — no owner has logged in for over "
                   f"{settings_row.inactivity_threshold_days} days.",
        )
        for m in Membership.objects.filter(business=business, role__system_role__in=["owner", "admin"], is_active=True):
            notify(
                business=business, level="critical",
                title="Business Continuity Mode activated",
                message=(
                    f"No owner has logged in for over {settings_row.inactivity_threshold_days} days. "
                    f"{settings_row.backup_manager.get_full_name() or settings_row.backup_manager.email} has been "
                    f"temporarily given owner-level access so the business isn't stuck. This reverts "
                    f"automatically the moment an owner logs back in."
                ),
                link_path="/security",
            )
        return activation

    if not owner_overdue and active_activation:
        active_activation.deactivated_at = now
        active_activation.deactivation_reason = "An owner logged back in."
        active_activation.save(update_fields=["deactivated_at", "deactivation_reason"])
        log_action(
            business=business, actor=None, action="permission_change", target=active_activation,
            new_value={"deactivated": True},
            reason="Business Continuity Mode deactivated — an owner logged back in.",
        )
        for m in Membership.objects.filter(business=business, role__system_role__in=["owner", "admin"], is_active=True):
            notify(
                business=business, level="important",
                title="Business Continuity Mode ended",
                message="An owner has logged back in — the backup manager's temporary elevated access has been removed.",
                link_path="/security",
            )
    return active_activation


def continuity_status(*, business):
    from .models import ContinuitySettings, ContinuityActivation
    settings_row = ContinuitySettings.objects.filter(business=business).first()
    active_activation = ContinuityActivation.objects.filter(business=business, deactivated_at__isnull=True).first()
    return {
        "is_enabled": bool(settings_row and settings_row.is_enabled),
        "backup_manager_id": str(settings_row.backup_manager_id) if settings_row and settings_row.backup_manager_id else None,
        "backup_manager_name": (
            settings_row.backup_manager.get_full_name() or settings_row.backup_manager.email
        ) if settings_row and settings_row.backup_manager else None,
        "inactivity_threshold_days": settings_row.inactivity_threshold_days if settings_row else None,
        "is_currently_active": bool(active_activation),
        "activated_at": active_activation.activated_at.isoformat() if active_activation else None,
    }
