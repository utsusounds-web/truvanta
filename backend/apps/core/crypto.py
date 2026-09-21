"""Field-level encryption at rest for credentials (integration tokens,
2FA secrets) stored in the database. Fully transparent — every place
that reads/writes an EncryptedCharField sees plain text, exactly like
any other CharField; encryption/decryption happens only at the DB
boundary, so nothing calling `platform.email_host_password` or
similar needs to change.

Key management: derives a Fernet key from Django's SECRET_KEY by
default (zero extra config — works out of the box). For a stronger
setup, set FIELD_ENCRYPTION_KEY in .env to a dedicated key (generate
one with `Fernet.generate_key()`), which decouples "rotate the app's
SECRET_KEY" from "re-encrypt every stored credential" — rotating
SECRET_KEY alone would otherwise make existing encrypted values
unreadable.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet() -> Fernet:
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "") or ""
    if key:
        return Fernet(key.encode() if isinstance(key, str) else key)
    # Derive a valid 32-byte urlsafe-base64 Fernet key from SECRET_KEY
    # so this works with zero extra configuration.
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    derived_key = base64.urlsafe_b64encode(digest)
    return Fernet(derived_key)


class EncryptedCharField(models.CharField):
    """Stores its value encrypted; reads/writes as plain text everywhere
    else. Existing plaintext rows (from before this field type was
    introduced) are read through unchanged rather than erroring, so
    this is safe to apply to a column that already has data."""

    def __init__(self, *args, **kwargs):
        # The encrypted ciphertext is longer than the plaintext — give
        # real headroom regardless of what max_length was requested for
        # the plaintext value, so encryption doesn't silently truncate.
        kwargs["max_length"] = max(kwargs.get("max_length", 255), 500)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        token = _get_fernet().encrypt(value.encode()).decode()
        return token

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Pre-existing plaintext value from before encryption was
            # added — return as-is rather than breaking the read.
            return value
