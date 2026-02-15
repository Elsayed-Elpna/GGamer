"""
Cookie-based JWT Authentication for enhanced security.
Uses HTTP-Only cookies instead of localStorage to prevent XSS attacks.
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from HTTP-Only cookies.
    Falls back to Authorization header if cookie is not present.
    """
    
    def authenticate(self, request):
        # Try to get token from cookie first
        raw_token = request.COOKIES.get('access_token')
        
        if raw_token is None:
            # Fallback to Authorization header for backward compatibility
            header = self.get_header(request)
            if header is None:
                return None
            
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None
        
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
    
    def enforce_csrf(self, request):
        """
        Enforce CSRF validation for cookie-based authentication.
        """
        check = CSRFCheck()
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f'CSRF Failed: {reason}')
