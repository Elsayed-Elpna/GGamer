"""
Comprehensive logging service for tracking authentication, admin actions, and suspicious activities.
"""
from common.models import AuthenticationLog, AdminActionLog, SuspiciousActivityLog
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('security')


class LoggingService:
    """
    Centralized logging service for all security-related events.
    """
    
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def get_user_agent(request):
        """Extract user agent from request"""
        return request.META.get('HTTP_USER_AGENT', '')
    
    # ==================== Authentication Logging ====================
    
    @staticmethod
    def log_authentication(user, email, action, request, success=True, failure_reason=None):
        """
        Log authentication events (login, logout, token refresh, etc.)
        
        Args:
            user: User object (can be None for failed logins)
            email: Email used in authentication
            action: AuthenticationLog.Action choice
            request: HTTP request object
            success: Whether the action was successful
            failure_reason: Reason for failure (if applicable)
        """
        try:
            log = AuthenticationLog.objects.create(
                user=user,
                email=email,
                action=action,
                success=success,
                failure_reason=failure_reason,
                ip_address=LoggingService.get_client_ip(request),
                user_agent=LoggingService.get_user_agent(request)
            )
            
            # Also log to file
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"[AUTH {status}] {action} - {email} from {log.ip_address}")
            
            return log
        except Exception as e:
            logger.error(f"Failed to create authentication log: {str(e)}")
            return None
    
    @staticmethod
    def check_failed_login_attempts(email, ip_address, time_window_minutes=15, max_attempts=5):
        """
        Check for multiple failed login attempts and log suspicious activity if threshold exceeded.
        
        Args:
            email: Email address
            ip_address: IP address
            time_window_minutes: Time window to check (default: 15 minutes)
            max_attempts: Maximum allowed failed attempts (default: 5)
            
        Returns:
            tuple: (is_locked, attempts_count)
        """
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        
        # Count failed login attempts
        failed_attempts = AuthenticationLog.objects.filter(
            email=email,
            action=AuthenticationLog.Action.FAILED_LOGIN,
            success=False,
            timestamp__gte=time_threshold
        ).count()
        
        # Check if account should be locked
        is_locked = failed_attempts >= max_attempts
        
        if is_locked:
            # Log suspicious activity
            LoggingService.log_suspicious_activity(
                activity_type=SuspiciousActivityLog.ActivityType.MULTIPLE_FAILED_LOGINS,
                details={
                    'email': email,
                    'failed_attempts': failed_attempts,
                    'time_window_minutes': time_window_minutes,
                },
                request=None,
                ip_address=ip_address,
                severity=SuspiciousActivityLog.Severity.HIGH
            )
        
        return is_locked, failed_attempts
    
    # ==================== Admin Action Logging ====================
    
    @staticmethod
    def log_admin_action(admin_user, action, request, target_user=None, details=None):
        """
        Log admin actions (ban, unban, role change, etc.)
        
        Args:
            admin_user: Admin user performing the action
            action: AdminActionLog.Action choice
            request: HTTP request object
            target_user: User affected by the action (optional)
            details: Additional details dict (optional)
        """
        try:
            log = AdminActionLog.objects.create(
                admin_user=admin_user,
                action=action,
                target_user=target_user,
                details=details or {},
                ip_address=LoggingService.get_client_ip(request)
            )
            
            # Also log to file
            target_str = f"→ {target_user.email}" if target_user else ""
            logger.warning(f"[ADMIN ACTION] {admin_user.email} {action} {target_str}")
            
            return log
        except Exception as e:
            logger.error(f"Failed to create admin action log: {str(e)}")
            return None
    
    # ==================== Suspicious Activity Logging ====================
    
    @staticmethod
    def log_suspicious_activity(activity_type, details, request=None, ip_address=None, 
                                user=None, severity=SuspiciousActivityLog.Severity.MEDIUM):
        """
        Log suspicious activities for security monitoring.
        
        Args:
            activity_type: SuspiciousActivityLog.ActivityType choice
            details: Details dict about the activity
            request: HTTP request object (optional)
            ip_address: IP address (optional, extracted from request if not provided)
            user: User involved (optional)
            severity: Severity level (default: MEDIUM)
        """
        try:
            if request:
                ip_address = ip_address or LoggingService.get_client_ip(request)
                user_agent = LoggingService.get_user_agent(request)
            else:
                user_agent = None
            
            log = SuspiciousActivityLog.objects.create(
                user=user,
                activity_type=activity_type,
                severity=severity,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Also log to file with appropriate level
            log_level = {
                SuspiciousActivityLog.Severity.LOW: logger.info,
                SuspiciousActivityLog.Severity.MEDIUM: logger.warning,
                SuspiciousActivityLog.Severity.HIGH: logger.error,
                SuspiciousActivityLog.Severity.CRITICAL: logger.critical,
            }.get(severity, logger.warning)
            
            user_str = user.email if user else "Unknown"
            log_level(f"[SUSPICIOUS {severity}] {activity_type} - {user_str} from {ip_address}")
            
            return log
        except Exception as e:
            logger.error(f"Failed to create suspicious activity log: {str(e)}")
            return None
    
    @staticmethod
    def log_banned_user_attempt(user, request):
        """Log when a banned user tries to access the system"""
        return LoggingService.log_suspicious_activity(
            activity_type=SuspiciousActivityLog.ActivityType.BANNED_USER_ATTEMPT,
            details={'email': user.email},
            request=request,
            user=user,
            severity=SuspiciousActivityLog.Severity.HIGH
        )
    
    @staticmethod
    def log_rate_limit_exceeded(user, endpoint, request):
        """Log when rate limit is exceeded"""
        return LoggingService.log_suspicious_activity(
            activity_type=SuspiciousActivityLog.ActivityType.RATE_LIMIT_EXCEEDED,
            details={
                'email': user.email if user else 'Anonymous',
                'endpoint': endpoint
            },
            request=request,
            user=user,
            severity=SuspiciousActivityLog.Severity.MEDIUM
        )
