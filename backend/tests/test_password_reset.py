from django.test import TestCase

from apps.accounts.password_reset import request_password_reset, confirm_password_reset, token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from tests.factories import make_user


class PasswordResetTests(TestCase):
    def test_request_reset_does_not_raise_for_unknown_email(self):
        # No account exists for this email — should silently no-op, never error.
        request_password_reset("nobody@nowhere.test")

    def test_confirm_reset_with_valid_token_changes_password(self):
        user = make_user("resettable@example.com", password="OldPass123!")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        success, error = confirm_password_reset(uid, token, "BrandNewPass456!")
        self.assertTrue(success)
        user.refresh_from_db()
        self.assertTrue(user.check_password("BrandNewPass456!"))

    def test_confirm_reset_with_invalid_token_fails(self):
        user = make_user("resettable2@example.com")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        success, error = confirm_password_reset(uid, "garbage-token", "BrandNewPass456!")
        self.assertFalse(success)
        self.assertIn("invalid", error.lower())

    def test_token_is_invalidated_after_password_change(self):
        user = make_user("resettable3@example.com", password="OldPass123!")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        confirm_password_reset(uid, token, "FirstNewPass789!")
        # Re-using the same token after the password already changed must fail —
        # otherwise a leaked reset link stays valid forever.
        success, error = confirm_password_reset(uid, token, "SecondNewPass000!")
        self.assertFalse(success)

    def test_weak_new_password_is_rejected(self):
        user = make_user("resettable4@example.com")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        success, error = confirm_password_reset(uid, token, "123")
        self.assertFalse(success)
