"""
Audit models - Central logging system.
Production-ready with comprehensive audit trails.
"""
import uuid
from django.db import models
from django.contrib.postgres.fields import JSONField
from apps.accounts.models import User


class AuditLog(models.Model):
    """
    Central audit log for all system events.
    Immutable record of all significant actions.
    """
    # Event categories
    AUTHENTICATION = 'AUTHENTICATION'
    ORDER = 'ORDER'
    PAYMENT = 'PAYMENT'
    ADMIN_ACTION = 'ADMIN_ACTION'
    DISPUTE = 'DISPUTE'
    REVIEW = 'REVIEW'
    VERIFICATION = 'VERIFICATION'
    CHAT = 'CHAT'
    API_REQUEST = 'API_REQUEST'
    
    CATEGORY_CHOICES = [
        (AUTHENTICATION, 'Authentication'),
        (ORDER, 'Order'),
        (PAYMENT, 'Payment'),
        (ADMIN_ACTION, 'Admin Action'),
        (DISPUTE, 'Dispute'),
        (REVIEW, 'Review'),
        (VERIFICATION, 'Verification'),
        (CHAT, 'Chat'),
        (API_REQUEST, 'API Request'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Event details
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    description = models.TextField()
    
    # User info
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    
    # Request info
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    
    # Additional data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context data"
    )
    
    # Result
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.category} - {self.action} at {self.created_at}"


class AuthenticationLog(models.Model):
    """
    Specialized authentication event logging.
    """
    # Event types
    LOGIN_SUCCESS = 'LOGIN_SUCCESS'
    LOGIN_FAILED = 'LOGIN_FAILED'
    LOGOUT = 'LOGOUT'
    PASSWORD_RESET = 'PASSWORD_RESET'
    PASSWORD_CHANGE = 'PASSWORD_CHANGE'
    TOKEN_REFRESH = 'TOKEN_REFRESH'
    
    EVENT_CHOICES = [
        (LOGIN_SUCCESS, 'Login Success'),
        (LOGIN_FAILED, 'Login Failed'),
        (LOGOUT, 'Logout'),
        (PASSWORD_RESET, 'Password Reset'),
        (PASSWORD_CHANGE, 'Password Change'),
        (TOKEN_REFRESH, 'Token Refresh'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    email = models.EmailField(help_text="Email used in attempt")
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Authentication Log'
        verbose_name_plural = 'Authentication Logs'
        indexes = [
            models.Index(fields=['email', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.email} at {self.created_at}"


class AdminActionLog(models.Model):
    """
    Log all admin/staff actions for accountability.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=100)
    target_model = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Action Log'
        verbose_name_plural = 'Admin Action Logs'
    
    def __str__(self):
        return f"Admin {self.admin} - {self.action} at {self.created_at}"


class RequestLog(models.Model):
    """
    Log API requests for monitoring and debugging.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500)
    query_params = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status_code = models.IntegerField()
    response_time_ms = models.IntegerField(help_text="Response time in milliseconds")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Request Log'
        verbose_name_plural = 'Request Logs'
        indexes = [
            models.Index(fields=['path', '-created_at']),
            models.Index(fields=['status_code', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code}"
