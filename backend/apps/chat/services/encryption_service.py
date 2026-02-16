"""
Chat encryption service.
Handles message encryption/decryption.
"""
from cryptography.fernet import Fernet
from django.conf import settings
import os


class ChatEncryptionService:
    """
    Service for encrypting/decrypting chat messages.
    Uses Fernet symmetric encryption (same as verification national IDs).
    """
    
    def __init__(self):
        """Initialize encryption with key from settings."""
        # Use same encryption key as verification app
        # In production, you may want separate keys
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            raise ValueError("ENCRYPTION_KEY not found in environment")
        
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt_message(self, message: str) -> bytes:
        """
        Encrypt a message.
        
        Args:
            message: Plain text message
            
        Returns:
            Encrypted message as bytes
        """
        if not message:
            return b''
        
        return self.cipher.encrypt(message.encode())
    
    def decrypt_message(self, encrypted_message: bytes) -> str:
        """
        Decrypt a message.
        
        Args:
            encrypted_message: Encrypted message bytes
            
        Returns:
            Decrypted plain text message
        """
        if not encrypted_message:
            return ''
        
        try:
            decrypted = self.cipher.decrypt(encrypted_message)
            return decrypted.decode()
        except Exception:
            return '[Decryption failed]'


# Global instance
encryption_service = ChatEncryptionService()
