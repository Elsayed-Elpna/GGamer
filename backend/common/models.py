"""
Comprehensive logging models for tracking authentication, admin actions, and suspicious activities.
"""
from django.db import models
from django.conf import settings


class AuthenticationLog(models.Model):
    """Log all authentication events"""
    
    class Action(models.TextChoices):
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        FAILED_LOGIN = 'FAILED_LOGIN', 'Failed Login'
        TOKEN_REFRESH = 'TOKEN_REFRESH', 'Token Refresh'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Password Reset'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auth_logs',
        null=True,
        blank=True,
        help_text="User (null for failed login attempts)"
    )
    email = models.EmailField(
        max_length=255,
        help_text="Email used in login attempt"
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        db_index=True
    )
    success = models.BooleanField(
        default=True,
        help_text="Whether the action was successful"
    )
    failure_reason = models.TextField(
        null=True,
        blank=True,
        help_text="Reason for failure (if applicable)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="Browser user agent string"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        db_table = 'auth_log'
        verbose_name = 'Authentication Log'
        verbose_name_plural = 'Authentication Logs'
        indexes = [
            models.Index(fields=['email', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['action', 'success']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.get_action_display()} - {self.email} @ {self.timestamp}"


class AdminActionLog(models.Model):
    """Log all admin actions"""
    
    class Action(models.TextChoices):
        BAN_USER = 'BAN_USER', 'Ban User'
        UNBAN_USER = 'UNBAN_USER', 'Unban User'
        CHANGE_ROLE = 'CHANGE_ROLE', 'Change User Role'
        VIEW_SENSITIVE_DATA = 'VIEW_SENSITIVE_DATA', 'View Sensitive Data'
        APPROVE_VERIFICATION = 'APPROVE_VERIFICATION', 'Approve Verification'
        REJECT_VERIFICATION = 'REJECT_VERIFICATION', 'Reject Verification'
        DELETE_USER = 'DELETE_USER', 'Delete User'
        MODIFY_USER = 'MODIFY_USER', 'Modify User'
    
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_actions_performed',
        help_text="Admin who performed the action"
    )
    action = models.CharField(
        max_length=30,
        choices=Action.choices,
        db_index=True
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_actions_received',
        help_text="User affected by the action (if applicable)"
    )
    details = models.JSONField(
        default=dict,
        help_text="Additional details about the action"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        db_table = 'admin_action_log'
        verbose_name = 'Admin Action Log'
        verbose_name_plural = 'Admin Action Logs'
        indexes = [
            models.Index(fields=['admin_user', 'timestamp']),
            models.Index(fields=['target_user', 'timestamp']),
            models.Index(fields=['action']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        target = f"→ {self.target_user.email}" if self.target_user else ""
        return f"{self.admin_user.email} {self.get_action_display()} {target} @ {self.timestamp}"


class SuspiciousActivityLog(models.Model):
    """Log suspicious activities for security monitoring"""
    
    class ActivityType(models.TextChoices):
        MULTIPLE_FAILED_LOGINS = 'MULTIPLE_FAILED_LOGINS', 'Multiple Failed Logins'
        UNUSUAL_ACCESS_PATTERN = 'UNUSUAL_ACCESS_PATTERN', 'Unusual Access Pattern'
        BANNED_USER_ATTEMPT = 'BANNED_USER_ATTEMPT', 'Banned User Access Attempt'
        RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED', 'Rate Limit Exceeded'
        INVALID_TOKEN = 'INVALID_TOKEN', 'Invalid Token Usage'
        SUSPICIOUS_FILE_UPLOAD = 'SUSPICIOUS_FILE_UPLOAD', 'Suspicious File Upload'
    
    class Severity(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        CRITICAL = 'CRITICAL', 'Critical'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suspicious_activities',
        null=True,
        blank=True,
        help_text="User involved (if known)"
    )
    activity_type = models.CharField(
        max_length=30,
        choices=ActivityType.choices,
        db_index=True
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
        db_index=True
    )
    details = models.JSONField(
        default=dict,
        help_text="Details about the suspicious activity"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    resolved = models.BooleanField(
        default=False,
        help_text="Whether the issue has been investigated/resolved"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_suspicious_activities'
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'suspicious_activity_log'
        verbose_name = 'Suspicious Activity Log'
        verbose_name_plural = 'Suspicious Activity Logs'
        indexes = [
            models.Index(fields=['activity_type', 'severity']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['resolved', 'severity']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        user_str = self.user.email if self.user else "Unknown"
        return f"[{self.severity}] {self.get_activity_type_display()} - {user_str} @ {self.timestamp}"
