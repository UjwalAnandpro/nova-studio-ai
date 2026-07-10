import os
import base64
import hashlib
from core.config.manager import settings_manager
from core.logger.custom_logger import log_action

class SecurityManager:
    """Provides secure local encryption and decryption of secrets (API Keys/credentials)."""
    def __init__(self):
        self.key_path = os.path.join(settings_manager.settings.storage_path, "secret.key")
        self.key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        if os.path.exists(self.key_path):
            try:
                with open(self.key_path, "rb") as f:
                    return f.read()
            except Exception:
                pass
        
        # Generate new base key
        new_key = os.urandom(32)
        try:
            os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
            with open(self.key_path, "wb") as f:
                f.write(new_key)
        except Exception as e:
            log_action("SecurityManager", "KeyGen", "WARNING", 0.0, f"Error saving secret key: {str(e)}")
        return new_key

    def encrypt(self, plaintext: str) -> str:
        """Encrypts sensitive plaintext strings to base64 tokens."""
        if not plaintext:
            return ""
        try:
            key_hash = hashlib.sha256(self.key).digest()
            plain_bytes = plaintext.encode("utf-8")
            
            # Simple XOR-rotation cipher (independent of external libs)
            cipher_bytes = bytearray(len(plain_bytes))
            for i in range(len(plain_bytes)):
                cipher_bytes[i] = plain_bytes[i] ^ key_hash[i % len(key_hash)]
                
            return base64.b64encode(cipher_bytes).decode("utf-8")
        except Exception as e:
            log_action("SecurityManager", "Encrypt", "FAILED", 0.0, f"Encryption failed: {str(e)}")
            return ""

    def decrypt(self, ciphertext: str) -> str:
        """Decrypts base64 ciphertext tokens back to original plaintext."""
        if not ciphertext:
            return ""
        try:
            key_hash = hashlib.sha256(self.key).digest()
            cipher_bytes = base64.b64decode(ciphertext.encode("utf-8"))
            
            plain_bytes = bytearray(len(cipher_bytes))
            for i in range(len(cipher_bytes)):
                plain_bytes[i] = cipher_bytes[i] ^ key_hash[i % len(key_hash)]
                
            return plain_bytes.decode("utf-8")
        except Exception as e:
            log_action("SecurityManager", "Decrypt", "FAILED", 0.0, f"Decryption failed: {str(e)}")
            return ""

# Singleton instance
security_manager = SecurityManager()
