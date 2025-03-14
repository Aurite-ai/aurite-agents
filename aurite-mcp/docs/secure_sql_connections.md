# Secure SQL Connections in Aurite MCP

This document outlines the security architecture for handling database connections in the Aurite MCP framework.

## Security Architecture

The Aurite MCP framework implements several layers of security to protect sensitive database credentials:

### 1. Security Manager

The central component of the security architecture is the `SecurityManager` implemented in `src/host/security.py`. This manager provides:

- Encryption of sensitive credentials
- Token-based credential access
- Permission controls for MCP servers
- Password masking and sensitive data detection

### 2. Security Flow

When connecting to databases through Aurite MCP, the following secure flow is used:

1. **Initial Connection Request**:
   - The client submits a connection request with credentials to an MCP Host
   - The MCP Host immediately secures the credentials using its SecurityManager

2. **Credential Storage**:
   - The raw connection string is encrypted using Fernet symmetric encryption
   - A secure access token is generated for this credential
   - Only the token and a masked connection string (with password replaced by asterisks) are returned

3. **Database Operations**:
   - All subsequent operations use the token or masked connection ID
   - Backend SQL servers resolve tokens through the SecurityManager
   - The actual credentials never appear in logs or responses

4. **Disconnection**:
   - When the connection is closed, the credentials are purged from memory

## Integration Points

### MCPHost Integration

The MCPHost class integrates the SecurityManager and provides methods to secure database connections:

```python
# Initialize with optional encryption key
host = MCPHost(config, encryption_key="your-encryption-key")

# Secure a database connection
token, masked_connection = await host.secure_database_connection(connection_string)
```

### SQL Server Integration

The SQL MCP Server has been enhanced to support token-based authentication:

```python
@mcp.tool()
def connect_database(connection_string: str, use_token: bool = False, ctx: Context = None)
```

When `use_token=True`, the connection_string is treated as a security token and resolved through the SecurityManager.

### Storage Router Integration

The Storage Router acts as a secure intermediary between clients and storage backends:

```python
@mcp.tool()
async def connect_storage(storage_type: str, connection_string: str, ctx: Context = None)
```

The router secures the connection string before passing it to backend servers and maintains a mapping of connection IDs to storage types.

## Configuration

### Encryption Key Management

For production environments, set the `AURITE_MCP_ENCRYPTION_KEY` environment variable to a secure encryption key. If not set, a random key will be generated, but this means credentials will not persist across restarts.

### Server Permissions

The MCPHost automatically registers permissions based on server capabilities:

```python
if "storage" in client_config.capabilities:
    await self._security_manager.register_server_permissions(
        client_config.client_id,
        allowed_credential_types=["database_connection"]
    )
```

This ensures only authorized servers can access specific credential types.

## Security Best Practices

1. **Always use HTTPS/TLS** for production MCP deployments to encrypt all transport
2. **Set a strong encryption key** and manage it securely
3. **Limit database user permissions** to only what is needed
4. **Configure firewalls** to restrict database access to the MCP host
5. **Rotate credentials** regularly
6. **Monitor logs** for suspicious connection attempts
7. **Consider using connection pooling** to minimize credential transfers

## Future Enhancements

1. **External Vault Integration**: Support for external secret management systems like HashiCorp Vault
2. **Time-Limited Credentials**: Automatic expiry of credential tokens
3. **Credential Rotation**: Automatic rotation of database credentials
4. **Audit Logging**: Enhanced logging for security events
5. **IAM Integration**: Support for cloud IAM-based authentication