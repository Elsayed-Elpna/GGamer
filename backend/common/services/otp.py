"""
OTP (One-Time Password) service for phone verification.
Currently uses mock SMS for development. Replace with real SMS provider in production.
"""
import random
import string
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class OTPService:
    """Service for generating and verifying OTP codes"""
    
    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10
    MAX_ATTEMPTS = 3
    RATE_LIMIT_MINUTES = 10
    
    @staticmethod
    def generate_otp() -> str:
        """Generate a 6-digit OTP code"""
        return ''.join(random.choices(string.digits, k=OTPService.OTP_LENGTH))
    
    @staticmethod
    def _get_cache_key(phone_number: str, suffix: str = '') -> str:
        """Generate cache key for OTP storage"""
        return f"otp_{phone_number}_{suffix}" if suffix else f"otp_{phone_number}"
    
    @classmethod
    def send_otp(cls, phone_number: str) -> dict:
        """
        Send OTP to phone number.
        
        Args:
            phone_number: Phone number to send OTP to
            
        Returns:
            dict with 'success', 'message', and optionally 'otp' (dev only)
        """
        # Check rate limiting
        attempts_key = cls._get_cache_key(phone_number, 'attempts')
        attempts = cache.get(attempts_key, 0)
        
        if attempts >= cls.MAX_ATTEMPTS:
            return {
                'success': False,
                'message': f'Too many OTP requests. Please try again in {cls.RATE_LIMIT_MINUTES} minutes.'
            }
        
        # Generate OTP
        otp = cls.generate_otp()
        
        # Store OTP in cache with expiry
        otp_key = cls._get_cache_key(phone_number)
        cache.set(otp_key, otp, timeout=cls.OTP_EXPIRY_MINUTES * 60)
        
        # Increment attempts
        cache.set(attempts_key, attempts + 1, timeout=cls.RATE_LIMIT_MINUTES * 60)
        
        # TODO: Replace with real SMS provider (Twilio, Vonage, etc.)
        # For now, log to console
        logger.info(f"📱 OTP for {phone_number}: {otp} (expires in {cls.OTP_EXPIRY_MINUTES} minutes)")
        
        # In development, return OTP in response
        # REMOVE THIS IN PRODUCTION!
        return {
            'success': True,
            'message': 'OTP sent successfully',
            'otp': otp,  # REMOVE IN PRODUCTION
            'expires_in_minutes': cls.OTP_EXPIRY_MINUTES
        }
    
    @classmethod
    def verify_otp(cls, phone_number: str, otp: str) -> dict:
        """
        Verify OTP code.
        
        Args:
            phone_number: Phone number to verify
            otp: OTP code to verify
            
        Returns:
            dict with 'success' and 'message'
        """
        otp_key = cls._get_cache_key(phone_number)
        stored_otp = cache.get(otp_key)
        
        if not stored_otp:
            return {
                'success': False,
                'message': 'OTP expired or not found. Please request a new one.'
            }
        
        if stored_otp != otp:
            return {
                'success': False,
                'message': 'Invalid OTP code.'
            }
        
        # OTP is valid, delete it
        cache.delete(otp_key)
        
        # Clear attempts counter
        attempts_key = cls._get_cache_key(phone_number, 'attempts')
        cache.delete(attempts_key)
        
        return {
            'success': True,
            'message': 'Phone number verified successfully'
        }


# Singleton instance
otp_service = OTPService()
