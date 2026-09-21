from django.test import TestCase

from apps.audit.services import log_action
from tests.factories import make_user, make_business_with_owner


class AuditImmutabilityTests(TestCase):
    def test_audit_log_cannot_be_modified_or_deleted(self):
        user = make_user()
        business, _ = make_business_with_owner(user)
        entry = log_action(business=business, actor=user, action="other", reason="test")

        entry.reason = "tampered"
        with self.assertRaises(ValueError):
            entry.save()

        with self.assertRaises(ValueError):
            entry.delete()
