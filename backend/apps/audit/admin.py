"""
Audit admin configuration.
"""
from django.contrib import admin
from apps.audit.models import AuditLog, AuthenticationLog, AdminActionLog, RequestLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['category', 'action', 'user', 'success', 'ip_address', 'created_at']
    list_filter = ['category', 'success', 'created_at']
    search_fields = ['action', 'description', 'user__email', 'ip_address']
    readonly_fields = [
        'id', 'category', 'action', 'description', 'user',
        'ip_address', 'user_agent', 'request_method', 'request_path',
        'metadata', 'success', 'error_message', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuthenticationLog)
class AuthenticationLogAdmin(admin.ModelAdmin):
    list_display = ['email', 'event_type', 'success', 'ip_address', 'created_at']
    list_filter = ['event_type', 'success', 'created_at']
    search_fields = ['email', 'ip_address']
    readonly_fields = [
        'id', 'user', 'email', 'event_type', 'ip_address',
        'user_agent', 'success', 'failure_reason', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ['admin', 'action', 'target_model', 'target_id', 'created_at']
    list_filter = ['action', 'target_model', 'created_at']
    search_fields = ['admin__email', 'action', 'description', 'target_id']
    readonly_fields = [
        'id', 'admin', 'action', 'target_model', 'target_id',
        'description', 'metadata', 'ip_address', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ['method', 'path', 'status_code', 'response_time_ms', 'user', 'created_at']
    list_filter = ['method', 'status_code', 'created_at']
    search_fields = ['path', 'user__email', 'ip_address']
    readonly_fields = [
        'id', 'user', 'method', 'path', 'query_params',
        'ip_address', 'user_agent', 'status_code', 'response_time_ms', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
