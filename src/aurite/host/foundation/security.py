"""
Security management for MCP host.
Handles credential management, encryption, and access control.
"""

import base64
import hashlib
import logging
import os
import re
import time
import warnings  # Add import
from dataclasses import dataclass
from typing import Any, Dict, Optional  # Added Type

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


# Patterns for sensitive data detection (Improved)
SENSITIVE_PATTERNS = {
    "database_url": r"(?:mysql|postgresql|postgres)(?:\+\w+)?://[^:]+:([^@]+)@[^/]+/\w+",  # Capture group 1 is password
    # Matches 'password' followed by optional space/quote, separator (:/=), optional space/quote, value (non-whitespace or quoted)
    "password": r"(password\s*['\"]?\s*[:=]\s*['\"]?)([^'\s\"]+)(['\"]?)",  # Capture group 1 is prefix, group 2 is value
    # Matches 'api_key', 'token', or 'API Key' followed by optional space/quote, separator (:/=), optional space/quote, value (non-whitespace or quoted)
    "api_key": r"((?:api[_\-]?key|token|API\sKey)\s*['\"]?\s*[:=]\s*['\"]?)([^'\s\"]+)(['\"]?)",  # Capture group 1 is prefix, group 2 is value
}


@dataclass
class Credential:
    """A secure credential with metadata"""

    id: str
    type: str  # e.g., "database", "api", "oauth"
    encrypted_value: str
    metadata: Dict[str, Any]
    expiry: Optional[int] = None  # Unix timestamp for expiry, if applicable


class SecurityManager:
    """
    Manages credentials, encryption, access tokens, and data masking for the MCP host.
    Handles secure storage (in-memory) and retrieval of sensitive information.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        # Initialize encryption key or generate one
        self._encryption_key = encryption_key or os.environ.get("AURITE_MCP_ENCRYPTION_KEY")
        if not self._encryption_key:
            self._encryption_key = self._generate_encryption_key()

        # Set up Fernet cipher for symmetric encryption
        self._cipher = self._setup_cipher(self._encryption_key)

        # In-memory credential store (in production, consider a secure vault service)
        self._credentials: Dict[str, Credential] = {}

        # Map of token IDs to credential IDs
        self._access_tokens: Dict[str, str] = {}

        # Server permissions removed as they are not currently used by the refactored host.

    async def initialize(self):
        """Initialize the security manager"""
        logger.debug("Initializing security manager")  # INFO -> DEBUG
        # Load credentials from secure storage if available

    def _generate_encryption_key(self) -> str:
        """Generate a new random encryption key"""
        key = Fernet.generate_key()
        key_str = base64.urlsafe_b64encode(key).decode("ascii")
        logger.debug("Generated new encryption key. For production, set AURITE_MCP_ENCRYPTION_KEY in environment.")
        return key_str

    def _setup_cipher(self, key: str | bytes) -> Fernet:  # Allow bytes input too
        """
        Set up encryption cipher from key.
        Fernet expects a urlsafe-base64-encoded 32-byte key.
        """
        key_bytes_for_fernet: bytes

        if isinstance(key, str):
            try:
                # Check if the string is valid base64 *without* decoding yet
                # This will raise an exception if not valid base64
                decoded_bytes_check = base64.urlsafe_b64decode(key.encode("ascii"))
                # If it is valid base64, Fernet wants it encoded as bytes
                key_bytes_for_fernet = key.encode("ascii")
                # Verify length after potential decode (Fernet does this internally, but good practice)
                if len(decoded_bytes_check) != 32:
                    raise ValueError("Provided base64 key must decode to 32 bytes.")

            except Exception:  # Includes binascii.Error and potentially others
                # If not a valid base64 string, derive a key
                logger.debug("Encryption key is not valid base64, deriving key from string.")
                salt = b"aurite-mcp-salt"  # Consistent salt
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,  # Fernet keys are 32 bytes raw
                    salt=salt,
                    iterations=100000,  # Standard recommendation
                )
                # Derive the raw 32 bytes
                derived_key_raw = kdf.derive(key.encode("utf-8"))
                # Fernet needs the base64 encoded version of the raw key
                key_bytes_for_fernet = base64.urlsafe_b64encode(derived_key_raw)

        elif isinstance(key, bytes):
            # Assume bytes are already urlsafe-base64-encoded
            key_bytes_for_fernet = key
            # Verify length after potential decode
            try:
                if len(base64.urlsafe_b64decode(key_bytes_for_fernet)) != 32:
                    raise ValueError("Provided key bytes must decode to 32 bytes.")
            except Exception as e:
                raise ValueError(f"Provided key bytes are not valid urlsafe-base64: {e}") from e
        else:
            raise TypeError("Encryption key must be a string or bytes.")

        # Fernet constructor handles the final base64 decoding
        return Fernet(key_bytes_for_fernet)

    # register_server_permissions method removed.

    async def store_credential(
        self,
        type: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,  # Changed to Optional
        expiry: Optional[int] = None,
    ) -> str:
        """
        Encrypt and store a credential, returning a credential ID
        """
        # Generate a unique ID for this credential
        cred_id = f"{type}_{hashlib.sha256(value.encode()).hexdigest()[:8]}"

        # Encrypt the value
        encrypted = self._cipher.encrypt(value.encode()).decode("ascii")

        # Store the credential
        self._credentials[cred_id] = Credential(
            id=cred_id,
            type=type,
            encrypted_value=encrypted,
            metadata=metadata or {},
            expiry=expiry,
        )

        logger.info(f"Stored credential {cred_id} of type {type}")
        return cred_id

    async def get_credential(self, cred_id: str) -> Optional[str]:
        """
        Retrieve and decrypt a credential by ID
        """
        if cred_id not in self._credentials:
            return None

        cred = self._credentials[cred_id]

        # Check expiry
        if cred.expiry and cred.expiry < time.time():
            warn_msg = f"Credential {cred_id} has expired"
            logger.warning(warn_msg)
            warnings.warn(warn_msg, UserWarning, stacklevel=2)  # Raise UserWarning
            return None

        # Decrypt
        try:
            value = self._cipher.decrypt(cred.encrypted_value.encode()).decode("utf-8")
            return value
        except Exception as e:
            logger.error(f"Failed to decrypt credential {cred_id}: {e}")
            return None

    async def create_access_token(self, cred_id: str) -> str:
        """
        Create a temporary access token for a credential
        Returns a token that can be used instead of the actual credential
        """
        if cred_id not in self._credentials:
            raise ValueError(f"Credential not found: {cred_id}")

        # Generate a token
        token = f"aurite-tk-{os.urandom(16).hex()}"

        # Map token to credential
        self._access_tokens[token] = cred_id

        return token

    async def resolve_access_token(self, token: str) -> Optional[str]:
        """
        Resolve an access token to the actual credential value
        """
        if token not in self._access_tokens:
            return None

        cred_id = self._access_tokens[token]
        return await self.get_credential(cred_id)

    # validate_server_access method removed.

    # secure_database_connection method removed.

    def mask_sensitive_data(self, data: str) -> str:
        """
        Mask sensitive data like passwords, API keys, and tokens in strings.
        """
        masked_data = data

        # Mask database URL passwords first
        # Reconstruct the string, replacing group 1 content with *****
        # Ensure group 1 exists before trying to replace
        def db_replacer(m):
            if m.group(1):  # Check if password group was captured
                # Replace the part of the full match that corresponds to group 1
                start, end = m.span(1)
                return m.group(0)[: start - m.start(0)] + "*****" + m.group(0)[end - m.start(0) :]
            return m.group(0)  # Return original match if no password captured

        masked_data = re.sub(SENSITIVE_PATTERNS["database_url"], db_replacer, masked_data)

        # Mask other password patterns (case-insensitive)
        masked_data = re.sub(
            SENSITIVE_PATTERNS["password"],
            lambda m: f"{m.group(1)}*****{m.group(3)}",
            masked_data,
            flags=re.IGNORECASE,  # Add ignorecase flag
        )

        # Mask API key/token patterns (case-insensitive)
        masked_data = re.sub(
            SENSITIVE_PATTERNS["api_key"],
            lambda m: f"{m.group(1)}*****{m.group(3)}",
            masked_data,
            flags=re.IGNORECASE,  # Add ignorecase flag
        )

        return masked_data

    async def shutdown(self):
        """Shutdown the security manager"""
        logger.debug("Shutting down security manager")

        # Clear credentials and tokens from memory
        self._credentials.clear()
        self._access_tokens.clear()
