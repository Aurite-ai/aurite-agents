from cryptography.fernet import Fernet
import base64

key_bytes = Fernet.generate_key()
key_str = base64.urlsafe_b64encode(key_bytes).decode("ascii")
print(f"Use this for AURITE_MCP_ENCRYPTION_KEY: {key_str}")
