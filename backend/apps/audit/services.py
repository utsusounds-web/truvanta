from django.contrib.contenttypes.models import ContentType

from .models import AuditLog


def log_action(
    *, business, actor, action, target=None, branch=None,
    previous_value=None, new_value=None, reason="", ip_address=None, device_info="",
):
    """Single entry point for writing an AuditLog row. Every module
    that performs a sensitive action (sale cancellation, price change,
    discount, refund, stock adjustment, permission change, login,
    receipt reprint, shift event...) should call this rather than
    creating AuditLog objects directly, so the shape stays consistent.
    """
    content_type = None
    object_id = None
    if target is not None:
        content_type = ContentType.objects.get_for_model(target)
        object_id = str(target.pk)

    return AuditLog.objects.create(
        business=business,
        branch=branch,
        actor=actor,
        action=action,
        content_type=content_type,
        object_id=object_id,
        previous_value=previous_value,
        new_value=new_value,
        reason=reason,
        ip_address=ip_address,
        device_info=device_info,
    )
