"""
Encryption service for sensitive data like National IDs.
Uses Fernet symmetric encryption with key from environment.
"""
import hashlib
import os
from cryptography.fernet import Fernet
from django.conf import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        # Get encryption key from settings or generate one
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
        
        if not encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY not found in settings. "
                "Add ENCRYPTION_KEY to your .env file. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        # Ensure key is bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
            
        self.cipher = Fernet(encryption_key)
    
    def encrypt_national_id(self, national_id: str) -> str:
        """
        Encrypt national ID for secure storage.
        
        Args:
            national_id: Plain text national ID
            
        Returns:
            Encrypted national ID as string
        """
        if not national_id:
            return ""
        
        # Convert to bytes and encrypt
        encrypted = self.cipher.encrypt(national_id.encode())
        return encrypted.decode()
    
    def decrypt_national_id(self, encrypted_national_id: str) -> str:
        """
        Decrypt national ID for display/verification.
        
        Args:
            encrypted_national_id: Encrypted national ID
            
        Returns:
            Plain text national ID
        """
        if not encrypted_national_id:
            return ""
        
        try:
            # Decrypt and convert to string
            decrypted = self.cipher.decrypt(encrypted_national_id.encode())
            return decrypted.decode()
        except Exception as e:
            # Log error but don't expose details
            print(f"Decryption error: {e}")
            return ""
    
    @staticmethod
    def hash_national_id(national_id: str) -> str:
        """
        Create SHA256 hash of national ID for duplicate detection.
        Hash is one-way and cannot be reversed.
        
        Args:
            national_id: Plain text national ID
            
        Returns:
            SHA256 hash as hex string
        """
        if not national_id:
            return ""
        
        # Create SHA256 hash
        return hashlib.sha256(national_id.encode()).hexdigest()


# Singleton instance
encryption_service = EncryptionService()
