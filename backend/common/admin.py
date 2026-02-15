"""
Admin panel configuration for logging models.
"""
from django.contrib import admin
from django.utils.html import format_html
from common.models import AuthenticationLog, AdminActionLog, SuspiciousActivityLog


@admin.register(AuthenticationLog)
class AuthenticationLogAdmin(admin.ModelAdmin):
    """Admin for authentication logs"""
    
    list_display = ['status_icon', 'action_display', 'email', 'ip_address', 'timestamp']
    list_filter = ['action', 'success', 'timestamp']
    search_fields = ['email', 'ip_address', 'user__email']
    readonly_fields = ['user', 'email', 'action', 'success', 'failure_reason', 
                      'ip_address', 'user_agent', 'timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Action Information', {
            'fields': ('user', 'email', 'action', 'success')
        }),
        ('Failure Details', {
            'fields': ('failure_reason',),
            'classes': ('collapse',)
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def status_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: green; font-size: 16px;">✓</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗</span>')
    status_icon.short_description = 'Status'
    
    def action_display(self, obj):
        colors = {
            'LOGIN': '#28A745',
            'LOGOUT': '#6C757D',
            'FAILED_LOGIN': '#DC3545',
            'TOKEN_REFRESH': '#007BFF',
            'PASSWORD_RESET': '#FFC107'
        }
        color = colors.get(obj.action, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display.short_description = 'Action'
    action_display.admin_order_field = 'action'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    """Admin for admin action logs"""
    
    list_display = ['admin_email', 'action_display', 'target_email', 'ip_address', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['admin_user__email', 'target_user__email', 'ip_address']
    readonly_fields = ['admin_user', 'action', 'target_user', 'details', 'ip_address', 'timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Action Information', {
            'fields': ('admin_user', 'action', 'target_user')
        }),
        ('Details', {
            'fields': ('details',)
        }),
        ('Request Information', {
            'fields': ('ip_address',)
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    def admin_email(self, obj):
        return obj.admin_user.email
    admin_email.short_description = 'Admin'
    admin_email.admin_order_field = 'admin_user__email'
    
    def target_email(self, obj):
        return obj.target_user.email if obj.target_user else '-'
    target_email.short_description = 'Target User'
    target_email.admin_order_field = 'target_user__email'
    
    def action_display(self, obj):
        colors = {
            'BAN_USER': '#DC3545',
            'UNBAN_USER': '#28A745',
            'CHANGE_ROLE': '#FFC107',
            'VIEW_SENSITIVE_DATA': '#17A2B8',
            'APPROVE_VERIFICATION': '#28A745',
            'REJECT_VERIFICATION': '#DC3545',
            'DELETE_USER': '#DC3545',
            'MODIFY_USER': '#007BFF'
        }
        color = colors.get(obj.action, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_display.short_description = 'Action'
    action_display.admin_order_field = 'action'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SuspiciousActivityLog)
class SuspiciousActivityLogAdmin(admin.ModelAdmin):
    """Admin for suspicious activity logs"""
    
    list_display = ['severity_badge', 'activity_display', 'user_email', 'ip_address', 
                   'resolved_status', 'timestamp']
    list_filter = ['activity_type', 'severity', 'resolved', 'timestamp']
    search_fields = ['user__email', 'ip_address', 'details']
    readonly_fields = ['user', 'activity_type', 'severity', 'details', 'ip_address', 
                      'user_agent', 'timestamp']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('user', 'activity_type', 'severity')
        }),
        ('Details', {
            'fields': ('details',)
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_by', 'resolved_at')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        }),
    )
    
    actions = ['mark_as_resolved']
    
    def severity_badge(self, obj):
        colors = {
            'LOW': '#28A745',
            'MEDIUM': '#FFC107',
            'HIGH': '#FF6B6B',
            'CRITICAL': '#DC3545'
        }
        color = colors.get(obj.severity, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.severity
        )
    severity_badge.short_description = 'Severity'
    severity_badge.admin_order_field = 'severity'
    
    def activity_display(self, obj):
        return obj.get_activity_type_display()
    activity_display.short_description = 'Activity'
    activity_display.admin_order_field = 'activity_type'
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Unknown'
    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'
    
    def resolved_status(self, obj):
        if obj.resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        return format_html('<span style="color: orange;">⚠ Pending</span>')
    resolved_status.short_description = 'Status'
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(
            resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now()
        )
        self.message_user(request, f'{count} suspicious activity(ies) marked as resolved.')
    mark_as_resolved.short_description = 'Mark selected as resolved'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
