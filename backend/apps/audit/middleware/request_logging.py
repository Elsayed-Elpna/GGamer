"""
Audit middleware - Log all requests.
"""
import time
from django.utils.deprecation import MiddlewareMixin
from apps.audit.models import RequestLog


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all API requests.
    Captures timing, user, IP, and response status.
    """
    
    def process_request(self, request):
        """Store request start time."""
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Log request after response is ready."""
        # Skip admin and static files
        if request.path.startswith('/admin/') or request.path.startswith('/static/'):
            return response
        
        # Calculate response time
        if hasattr(request, '_start_time'):
            response_time = int((time.time() - request._start_time) * 1000)
        else:
            response_time = 0
        
        # Get user
        user = request.user if request.user.is_authenticated else None
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Log request (async to avoid slowing down response)
        try:
            RequestLog.objects.create(
                user=user,
                method=request.method,
                path=request.path[:500],
                query_params=request.META.get('QUERY_STRING', '')[:500],
                ip_address=ip_address,
                user_agent=user_agent[:500],
                status_code=response.status_code,
                response_time_ms=response_time
            )
        except Exception:
            # Don't let logging errors break requests
            pass
        
        return response
