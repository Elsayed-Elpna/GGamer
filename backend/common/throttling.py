"""
Custom throttle classes for rate limiting verification endpoints.
SECURITY: Prevents OTP flooding, abuse, and brute force attacks.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class OTPThrottle(UserRateThrottle):
    """
    Throttle for OTP sending endpoints.
    Limits users to 5 OTP requests per hour to prevent SMS flooding.
    """
    rate = '5/hour'
    scope = 'otp'


class OTPVerifyThrottle(UserRateThrottle):
    """
    Throttle for OTP verification endpoint.
    Limits to 3 verification attempts per hour to prevent brute force.
    SECURITY: Prevents attackers from trying all 1 million 6-digit combinations.
    """
    rate = '3/hour'
    scope = 'otp_verify'


class AuthThrottle(AnonRateThrottle):
    """
    Throttle for authentication endpoints (login, register).
    Limits to 10 attempts per hour to prevent brute force attacks.
    """
    rate = '10/hour'
    scope = 'auth'


class VerificationThrottle(UserRateThrottle):
    """
    Throttle for verification submission endpoints.
    Limits to 10 submissions per day to prevent abuse.
    """
    rate = '10/day'
    scope = 'verification'
