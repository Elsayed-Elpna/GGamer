"""
Dispute admin configuration.
"""
from django.contrib import admin
from apps.disputes.models import (
    Dispute, DisputeEvidence, DisputeMessage, DisputeDecision
)


class DisputeEvidenceInline(admin.TabularInline):
    model = DisputeEvidence
    extra = 0
    readonly_fields = ['uploaded_by', 'file', 'file_type', 'file_size', 'description', 'created_at']
    can_delete = False


class DisputeMessageInline(admin.TabularInline):
    model = DisputeMessage
    extra = 0
    readonly_fields = ['sender', 'message', 'is_internal', 'created_at']
    can_delete = False


class DisputeDecisionInline(admin.TabularInline):
    model = DisputeDecision
    extra = 0
    readonly_fields = [
        'admin', 'decision_type', 'buyer_refund_amount',
        'seller_release_amount', 'reason', 'ip_address', 'created_at'
    ]
    can_delete = False


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'created_by_role', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'created_by_role', 'created_at']
    search_fields = ['id', 'order__id', 'reason']
    readonly_fields = [
        'id', 'order', 'created_by_user', 'created_by_role',
        'reason', 'description', 'created_at', 'updated_at', 'resolved_at'
    ]
    fields = [
        'id', 'order', 'created_by_user', 'created_by_role',
        'reason', 'description', 'status', 'assigned_to',
        'created_at', 'updated_at', 'resolved_at'
    ]
    inlines = [DisputeEvidenceInline, DisputeMessageInline, DisputeDecisionInline]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
