"""
Security management for MCP host.
Handles credential management, encryption, and access control.
"""

import os
import re
import logging
import base64
import hashlib
import time
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Patterns for sensitive data detection
SENSITIVE_PATTERNS = {
    "database_url": r"(?:mysql|postgresql|postgres)(?:\+\w+)?://[^:]+:[^@]+@[^/]+/\w+",
    "password": r"password['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
    "api_key": r"(?:api[_\-]?key|token)['\"]?\s*[:=]\s*['\"]([^'\"]+)['\"]",
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
    Manages credentials, encryption, and security policies for the MCP host.
    Handles secure storage and retrieval of sensitive information.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        # Initialize encryption key or generate one
        self._encryption_key = encryption_key or os.environ.get(
            "AURITE_MCP_ENCRYPTION_KEY"
        )
        if not self._encryption_key:
            self._encryption_key = self._generate_encryption_key()

        # Set up Fernet cipher for symmetric encryption
        self._cipher = self._setup_cipher(self._encryption_key)

        # In-memory credential store (in production, consider a secure vault service)
        self._credentials: Dict[str, Credential] = {}

        # Map of token IDs to credential IDs
        self._access_tokens: Dict[str, str] = {}

        # Map of server IDs to allowed credential types
        self._server_permissions: Dict[str, List[str]] = {}

    async def initialize(self):
        """Initialize the security manager"""
        logger.info("Initializing security manager")
        # Load credentials from secure storage if available

    def _generate_encryption_key(self) -> str:
        """Generate a new random encryption key"""
        key = Fernet.generate_key()
        key_str = base64.urlsafe_b64encode(key).decode("ascii")
        logger.warning(
            "Generated new encryption key. For production, set AURITE_MCP_ENCRYPTION_KEY in environment."
        )
        return key_str

    def _setup_cipher(self, key: str) -> Fernet:
        """Set up encryption cipher from key"""
        # Handle string or bytes key
        if isinstance(key, str):
            try:
                key_bytes = base64.urlsafe_b64decode(key.encode("ascii"))
            except Exception:
                # If not a valid base64 key, derive a key from the string
                salt = b"aurite-mcp-salt"  # Not for security, just consistency
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode("utf-8")))
        else:
            key_bytes = key

        return Fernet(key_bytes)

    async def register_server_permissions(
        self, server_id: str, allowed_credential_types: List[str]
    ):
        """Register which credential types a server is allowed to access"""
        self._server_permissions[server_id] = allowed_credential_types
        logger.info(
            f"Registered permissions for server {server_id}: {allowed_credential_types}"
        )

    async def store_credential(
        self,
        type: str,
        value: str,
        metadata: Dict[str, Any] = None,
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
            logger.warning(f"Credential {cred_id} has expired")
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

    async def validate_server_access(self, server_id: str, cred_id: str) -> bool:
        """
        Validate if a server is allowed to access a specific credential
        """
        if server_id not in self._server_permissions:
            return False

        if cred_id not in self._credentials:
            return False

        # Check if server has permission for this credential type
        allowed_types = self._server_permissions[server_id]
        cred_type = self._credentials[cred_id].type

        return cred_type in allowed_types

    async def secure_database_connection(
        self, connection_string: str
    ) -> Tuple[str, str]:
        """
        Securely handle a database connection string.
        Returns a token and masked connection string.

        The token can be used to retrieve the actual connection string.
        The masked string is safe to log or return to clients.
        """
        # Store the connection string as a credential
        cred_id = await self.store_credential(
            type="database_connection",
            value=connection_string,
            metadata={"purpose": "sql_connection"},
        )

        # Create an access token
        token = await self.create_access_token(cred_id)

        # Create a masked version for display
        masked = self.mask_sensitive_data(connection_string)

        return token, masked

    def mask_sensitive_data(self, data: str) -> str:
        """
        Mask sensitive data like passwords in strings
        """
        # For database URLs, mask the password
        if re.search(SENSITIVE_PATTERNS["database_url"], data):
            return re.sub(r"://([^:]+):([^@]+)@", r"://\1:*****@", data)

        # For other patterns, just mask appropriately
        for pattern in SENSITIVE_PATTERNS.values():
            data = re.sub(
                pattern, lambda m: m.group(0).replace(m.group(1), "*****"), data
            )

        return data

    async def shutdown(self):
        """Shutdown the security manager"""
        logger.info("Shutting down security manager")

        # Clear all credentials from memory
        self._credentials.clear()
        self._access_tokens.clear()
        self._server_permissions.clear()
