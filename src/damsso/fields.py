"""
Custom encrypted fields for storing sensitive data.

Uses Fernet symmetric encryption from the cryptography library.
"""

from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.encoding import force_bytes, force_str


def get_fernet() -> MultiFernet:
    """
    Get a MultiFernet instance for encryption/decryption.

    Supports multiple keys for key rotation:
    - The first key is used for encryption
    - All keys are tried for decryption

    Raises:
        ImproperlyConfigured: If FERNET_KEYS is not configured
    """
    keys = getattr(settings, "FERNET_KEYS", None)
    if not keys:
        raise ImproperlyConfigured(
            "FERNET_KEYS setting is required for encrypted fields. "
            "Generate a key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    if not isinstance(keys, (list, tuple)):
        keys = [keys]

    # Convert all keys to bytes and create Fernet instances
    fernet_keys = []
    for key in keys:
        if isinstance(key, str):
            key = key.encode()
        try:
            fernet_keys.append(Fernet(key))
        except Exception as e:
            raise ImproperlyConfigured(f"Invalid Fernet key in FERNET_KEYS: {e}")

    return MultiFernet(fernet_keys)


class EncryptedFieldMixin:
    """
    Mixin for encrypted fields.

    Provides encryption/decryption methods using Fernet.
    """

    def get_fernet(self) -> MultiFernet:
        """Get the Fernet instance for encryption/decryption."""
        return get_fernet()

    def encrypt_value(self, value: Optional[str]) -> Optional[bytes]:
        """
        Encrypt a value using Fernet.

        Args:
            value: The plaintext value to encrypt

        Returns:
            The encrypted value as bytes, or None if value is None/empty
        """
        if not value:
            return None

        fernet = self.get_fernet()
        plaintext = force_bytes(value)
        return fernet.encrypt(plaintext)

    def decrypt_value(self, value: Optional[bytes]) -> Optional[str]:
        """
        Decrypt a value using Fernet.

        Args:
            value: The encrypted value as bytes

        Returns:
            The decrypted plaintext value, or None if value is None/empty
        """
        if not value:
            return None

        fernet = self.get_fernet()
        try:
            plaintext = fernet.decrypt(force_bytes(value))
            return force_str(plaintext)
        except InvalidToken:
            raise ValueError("Unable to decrypt value - invalid encryption key or corrupted data")


class EncryptedCharField(EncryptedFieldMixin, models.BinaryField):
    """
    A CharField that encrypts its contents using Fernet symmetric encryption.

    The value is encrypted before being stored in the database and decrypted
    when retrieved. Transparent to application code.

    Usage:
        oidc_secret = EncryptedCharField(max_length=500, blank=True)

    Configuration:
        Requires FERNET_KEYS in settings.py:

        FERNET_KEYS = [
            'your-encryption-key-here',  # Used for new encryptions
            'old-key-if-rotating',       # Can still decrypt old data
        ]

        Generate a key:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """

    def __init__(self, *args, **kwargs):
        # Remove max_length since BinaryField doesn't use it
        # But we keep it in kwargs for help_text purposes
        self._max_length = kwargs.pop('max_length', None)
        # Make the field editable (BinaryField is non-editable by default)
        kwargs.setdefault('editable', True)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value: Any) -> Optional[bytes]:
        """
        Convert the value for database storage (encrypt it).

        Args:
            value: The plaintext value

        Returns:
            The encrypted value as bytes
        """
        if value is None or value == '':
            return None

        # If it's already bytes, assume it's already encrypted
        if isinstance(value, bytes):
            return value

        return self.encrypt_value(str(value))

    def from_db_value(self, value: Optional[bytes], expression, connection) -> Optional[str]:
        """
        Convert the value from the database (decrypt it).

        Args:
            value: The encrypted value from database
            expression: The query expression
            connection: The database connection

        Returns:
            The decrypted plaintext value
        """
        if value is None:
            return None

        return self.decrypt_value(value)

    def to_python(self, value: Any) -> Optional[str]:
        """
        Convert the value to a Python object (decrypt if needed).

        Args:
            value: The value from the database or form

        Returns:
            The decrypted plaintext value
        """
        if value is None or value == '':
            return None

        # If it's already a string, it's already decrypted
        if isinstance(value, str):
            return value

        # If it's bytes, decrypt it
        if isinstance(value, bytes):
            return self.decrypt_value(value)

        return str(value)


class EncryptedTextField(EncryptedFieldMixin, models.BinaryField):
    """
    A TextField that encrypts its contents using Fernet symmetric encryption.

    Similar to EncryptedCharField but for larger text content.

    Usage:
        certificate = EncryptedTextField(blank=True)

    Configuration:
        Requires FERNET_KEYS in settings.py (see EncryptedCharField for details)
    """

    def __init__(self, *args, **kwargs):
        # Make the field editable (BinaryField is non-editable by default)
        kwargs.setdefault('editable', True)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value: Any) -> Optional[bytes]:
        """
        Convert the value for database storage (encrypt it).

        Args:
            value: The plaintext value

        Returns:
            The encrypted value as bytes
        """
        if value is None or value == '':
            return None

        # If it's already bytes, assume it's already encrypted
        if isinstance(value, bytes):
            return value

        return self.encrypt_value(str(value))

    def from_db_value(self, value: Optional[bytes], expression, connection) -> Optional[str]:
        """
        Convert the value from the database (decrypt it).

        Args:
            value: The encrypted value from database
            expression: The query expression
            connection: The database connection

        Returns:
            The decrypted plaintext value
        """
        if value is None:
            return None

        return self.decrypt_value(value)

    def to_python(self, value: Any) -> Optional[str]:
        """
        Convert the value to a Python object (decrypt if needed).

        Args:
            value: The value from the database or form

        Returns:
            The decrypted plaintext value
        """
        if value is None or value == '':
            return None

        # If it's already a string, it's already decrypted
        if isinstance(value, str):
            return value

        # If it's bytes, decrypt it
        if isinstance(value, bytes):
            return self.decrypt_value(value)

        return str(value)
