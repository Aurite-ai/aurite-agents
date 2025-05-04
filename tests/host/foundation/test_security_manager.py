"""
Unit tests for the SecurityManager.
"""

import pytest
import os
import base64
import time # Add missing import
from unittest.mock import patch, MagicMock

# Import the class to test
from src.host.foundation.security import SecurityManager, Fernet

# Mark tests as host_unit
pytestmark = [pytest.mark.host_unit, pytest.mark.anyio] # Add anyio marker


# --- Fixtures ---

@pytest.fixture
def security_manager() -> SecurityManager:
    """Fixture to provide a SecurityManager instance with a generated key."""
    # Use a generated key for simplicity in unit tests
    return SecurityManager()

# --- Test Cases ---


def test_security_manager_init_with_provided_key():
    """Test initialization with a valid base64 key provided directly."""
    test_key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    with patch("src.host.foundation.security.Fernet") as mock_fernet:
        manager = SecurityManager(encryption_key=test_key)
        assert manager._encryption_key == test_key
        # Assert Fernet is called with the encoded key bytes
        mock_fernet.assert_called_once_with(test_key.encode("ascii"))
        assert manager._cipher is not None


def test_security_manager_init_with_env_var_key():
    """Test initialization using a valid base64 key from environment variable."""
    test_key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    env_var = "AURITE_MCP_ENCRYPTION_KEY"
    original_value = os.environ.get(env_var)
    os.environ[env_var] = test_key
    try:
        # Indent the 'with' block under 'try'
        with patch("src.host.foundation.security.Fernet") as mock_fernet:
            manager = SecurityManager()  # No key passed directly
            assert manager._encryption_key == test_key
            # Assert Fernet is called with the encoded key bytes
        mock_fernet.assert_called_once_with(test_key.encode("ascii"))
        assert manager._cipher is not None
    finally:
        # Restore original environment variable state
        if original_value is None:
            del os.environ[env_var]
        else:
            os.environ[env_var] = original_value


def test_security_manager_init_generate_key():
    """Test key generation when no key is provided."""
    env_var = "AURITE_MCP_ENCRYPTION_KEY"
    original_value = os.environ.get(env_var)
    if env_var in os.environ:
        del os.environ[env_var]  # Ensure env var is not set

    try:
        # Patch Fernet.generate_key to return a predictable key for assertion
        generated_key_bytes = os.urandom(32)
        generated_key_str = base64.urlsafe_b64encode(generated_key_bytes).decode(
            "ascii"
        )
        # ONLY patch Fernet.generate_key
        with patch(
            "src.host.foundation.security.Fernet.generate_key",
            return_value=generated_key_bytes,
        ):
            manager = SecurityManager()
            # Check the generated key string is stored
            assert manager._encryption_key == generated_key_str
            # Check that a cipher was actually created (implies _setup_cipher worked)
            assert manager._cipher is not None
            # We can't easily assert on the Fernet() call without more patching,
            # but verifying the key and cipher existence is a good start.
    finally:
        # Restore environment variable
        if original_value is not None:
            os.environ[env_var] = original_value


def test_security_manager_init_derive_key_from_string():
    """Test key derivation when a non-base64 string is provided."""
    test_string_key = "this-is-not-a-base64-key"
    # We expect PBKDF2HMAC to be used to derive a key.
    # Force the initial base64 decode attempt to fail to ensure the except block is hit.
    with patch(
        "src.host.foundation.security.base64.urlsafe_b64decode",
        side_effect=ValueError("Simulated decode error"),
    ), patch("src.host.foundation.security.PBKDF2HMAC") as mock_kdf_class, patch(
        "src.host.foundation.security.Fernet"
    ) as mock_fernet:
        # Mock the derive method of the KDF instance
        mock_kdf_instance = MagicMock()
        derived_key_bytes = os.urandom(32)  # Simulate derived key
        mock_kdf_instance.derive.return_value = derived_key_bytes
        mock_kdf_class.return_value = mock_kdf_instance

        manager = SecurityManager(encryption_key=test_string_key)

        assert manager._encryption_key == test_string_key
        # Check KDF was used
        mock_kdf_class.assert_called_once()
        mock_kdf_instance.derive.assert_called_once_with(
            test_string_key.encode("utf-8")
        )
        # Check Fernet was initialized with the base64 encoded derived key
        expected_fernet_key = base64.urlsafe_b64encode(derived_key_bytes)
        mock_fernet.assert_called_once_with(expected_fernet_key)
        assert manager._cipher is not None


# --- Credential Storage and Retrieval Tests ---

async def test_store_and_get_credential(security_manager: SecurityManager):
    """Test storing and retrieving a simple credential."""
    cred_type = "api_key"
    cred_value = "my-secret-api-key-12345"
    metadata = {"service": "test_service"}

    # Store the credential
    cred_id = await security_manager.store_credential(
        type=cred_type, value=cred_value, metadata=metadata
    )

    assert isinstance(cred_id, str)
    assert cred_id.startswith(cred_type)
    assert cred_id in security_manager._credentials # Check internal storage

    # Retrieve the credential
    retrieved_value = await security_manager.get_credential(cred_id)

    assert retrieved_value == cred_value

    # Verify internal storage details (optional but good for debugging)
    stored_cred = security_manager._credentials[cred_id]
    assert stored_cred.id == cred_id
    assert stored_cred.type == cred_type
    assert stored_cred.metadata == metadata
    assert stored_cred.expiry is None
    # Check that the stored value is actually encrypted (different from original)
    assert stored_cred.encrypted_value != cred_value


async def test_get_credential_not_found(security_manager: SecurityManager):
    """Test retrieving a non-existent credential returns None."""
    retrieved_value = await security_manager.get_credential("non_existent_id")
    assert retrieved_value is None


async def test_get_credential_expired(security_manager: SecurityManager):
    """Test retrieving an expired credential returns None."""
    cred_type = "temp_token"
    cred_value = "expired-secret"
    # Store with an expiry time in the past
    past_expiry = int(time.time()) - 60 # 1 minute ago

    cred_id = await security_manager.store_credential(
        type=cred_type, value=cred_value, expiry=past_expiry
    )

    # Attempt to retrieve
    with pytest.warns(UserWarning, match=f"Credential {cred_id} has expired"):
        retrieved_value = await security_manager.get_credential(cred_id)

    assert retrieved_value is None


async def test_store_credential_same_value_different_type(security_manager: SecurityManager):
    """Test storing the same value with different types results in different IDs."""
    cred_value = "same-secret-value"
    cred_id_1 = await security_manager.store_credential(type="type1", value=cred_value)
    cred_id_2 = await security_manager.store_credential(type="type2", value=cred_value)

    assert cred_id_1 != cred_id_2
    assert cred_id_1.startswith("type1")
    assert cred_id_2.startswith("type2")
    assert await security_manager.get_credential(cred_id_1) == cred_value
    assert await security_manager.get_credential(cred_id_1) == cred_value
    assert await security_manager.get_credential(cred_id_2) == cred_value


# --- Access Token Tests ---

async def test_create_and_resolve_access_token(security_manager: SecurityManager):
    """Test creating an access token and resolving it back to the credential value."""
    cred_type = "db_pass"
    cred_value = "super_secret_db_password"
    cred_id = await security_manager.store_credential(type=cred_type, value=cred_value)

    # Create token
    token = await security_manager.create_access_token(cred_id)

    assert isinstance(token, str)
    assert token.startswith("aurite-tk-")
    assert token in security_manager._access_tokens # Check internal storage
    assert security_manager._access_tokens[token] == cred_id

    # Resolve token
    resolved_value = await security_manager.resolve_access_token(token)
    assert resolved_value == cred_value


async def test_create_access_token_invalid_cred_id(security_manager: SecurityManager):
    """Test creating a token for a non-existent credential raises ValueError."""
    with pytest.raises(ValueError, match="Credential not found: invalid_id"):
        await security_manager.create_access_token("invalid_id")


async def test_resolve_access_token_invalid_token(security_manager: SecurityManager):
    """Test resolving an invalid or non-existent token returns None."""
    resolved_value = await security_manager.resolve_access_token("invalid-token-format")
    assert resolved_value is None


async def test_resolve_access_token_for_expired_credential(security_manager: SecurityManager):
    """Test resolving a token for an expired credential returns None."""
    cred_type = "expired_api"
    cred_value = "some_api_key"
    past_expiry = int(time.time()) - 60
    cred_id = await security_manager.store_credential(
        type=cred_type, value=cred_value, expiry=past_expiry
    )
    token = await security_manager.create_access_token(cred_id)

    # Attempt to resolve, expect None due to expiry check in get_credential
    with pytest.warns(UserWarning, match=f"Credential {cred_id} has expired"):
         resolved_value = await security_manager.resolve_access_token(token)

    assert resolved_value is None


# TODO: Add tests for mask_sensitive_data
# TODO: Add tests for resolve_gcp_secrets (mocking GCP client)
