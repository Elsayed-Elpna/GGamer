"""
Custom middleware for security and logging.
"""
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('security')


class BannedUserMiddleware(MiddlewareMixin):
    """
    Middleware to block banned users from accessing any authenticated endpoint.
    This provides a global ban enforcement layer.
    """
    
    def process_request(self, request):
        # Skip for unauthenticated requests
        if not request.user.is_authenticated:
            return None
        
        # Check if user is banned
        if request.user.is_banned:
            logger.warning(
                f"Banned user attempted access: {request.user.email} "
                f"(User ID: {request.user.id}, Path: {request.path})"
            )
            
            return JsonResponse(
                {
                    'error': 'Account banned',
                    'detail': request.user.ban_reason or 'Your account has been banned. Please contact support.',
                    'support_email': 'support@ggamer.com'
                },
                status=403
            )
        
        return None


class SecurityLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log security-relevant events.
    """
    
    # Paths that should be logged
    MONITORED_PATHS = [
        '/api/auth/login/',
        '/api/accounts/register/',
        '/api/accounts/ban/',
        '/api/accounts/private-profile/',
    ]
    
    def process_response(self, request, response):
        # Only log monitored paths
        if not any(request.path.startswith(path) for path in self.MONITORED_PATHS):
            return response
        
        # Log failed authentication attempts
        if request.path.startswith('/api/auth/login/') and response.status_code == 401:
            email = request.data.get('email', 'unknown') if hasattr(request, 'data') else 'unknown'
            logger.warning(
                f"Failed login attempt: {email} from IP {self.get_client_ip(request)}"
            )
        
        # Log successful registrations
        if request.path.startswith('/api/accounts/register/') and response.status_code == 201:
            email = request.data.get('email', 'unknown') if hasattr(request, 'data') else 'unknown'
            logger.info(
                f"New user registration: {email} from IP {self.get_client_ip(request)}"
            )
        
        # Log user bans
        if request.path.startswith('/api/accounts/ban/') and response.status_code == 200:
            if request.user.is_authenticated:
                logger.warning(
                    f"User banned by admin: {request.user.email} (Admin ID: {request.user.id})"
                )
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
