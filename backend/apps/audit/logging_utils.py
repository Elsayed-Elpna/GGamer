"""
Audit logging utilities.
Helper functions for creating audit logs throughout the system.
"""
from typing import Optional, Dict, Any
from apps.audit.models import AuditLog, AuthenticationLog, AdminActionLog
from apps.accounts.models import User


class AuditLogger:
    """
    Centralized audit logging service.
    Use throughout the application for consistent logging.
    """
    
    @staticmethod
    def log_authentication(
        email: str,
        event_type: str,
        success: bool,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
        failure_reason: str = ""
    ) -> AuthenticationLog:
        """
        Log authentication event.
        
        Args:
            email: Email used in attempt
            event_type: Type of auth event
            success: Whether successful
            user: User object if authenticated
            ip_address: IP address
            user_agent: Browser/app info
            failure_reason: Reason for failure
            
        Returns:
            Created AuthenticationLog
        """
        return AuthenticationLog.objects.create(
            user=user,
            email=email,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent[:500],
            success=success,
            failure_reason=failure_reason[:200]
        )
    
    @staticmethod
    def log_admin_action(
        admin: User,
        action: str,
        description: str,
        target_model: str = "",
        target_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AdminActionLog:
        """
        Log admin action.
        
        Args:
            admin: Admin user
            action: Action name
            description: Description of action
            target_model: Model affected
            target_id: ID of affected object
            metadata: Additional data
            ip_address: Admin IP
            
        Returns:
            Created AdminActionLog
        """
        return AdminActionLog.objects.create(
            admin=admin,
            action=action[:100],
            target_model=target_model[:50],
            target_id=str(target_id)[:100],
            description=description,
            metadata=metadata or {},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_event(
        category: str,
        action: str,
        description: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
        user_agent: str = "",
        request_method: str = "",
        request_path: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: str = ""
    ) -> AuditLog:
        """
        Log general system event.
        
        Args:
            category: Event category
            action: Action name
            description: Event description
            user: User involved
            ip_address: IP address
            user_agent: User agent
            request_method: HTTP method
            request_path: Request path
            metadata: Additional context
            success: Whether successful
            error_message: Error if failed
            
        Returns:
            Created AuditLog
        """
        return AuditLog.objects.create(
            category=category,
            action=action[:100],
            description=description,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent[:500],
            request_method=request_method[:10],
            request_path=request_path[:500],
            metadata=metadata or {},
            success=success,
            error_message=error_message
        )


# Convenience instance
audit_logger = AuditLogger()
