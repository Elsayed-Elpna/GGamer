"""
Order admin configuration.
"""
from django.contrib import admin
from apps.orders.models import Order, OrderStateLog, EscrowAccount, ProofUpload


class OrderStateLogInline(admin.TabularInline):
    model = OrderStateLog
    extra = 0
    readonly_fields = ['from_state', 'to_state', 'changed_by', 'reason', 'ip_address', 'created_at']
    can_delete = False


class ProofUploadInline(admin.TabularInline):
    model = ProofUpload
    extra = 0
    readonly_fields = ['uploaded_by', 'file_type', 'file', 'description', 'created_at']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'seller', 'state', 'total_amount', 'created_at']
    list_filter = ['state', 'created_at']
    search_fields = ['id', 'buyer__email', 'seller__email']
    readonly_fields = [
        'id', 'buyer', 'seller', 'offer', 'quantity', 'unit_price',
        'total_amount', 'platform_fee', 'seller_amount', 'state',
        'created_at', 'updated_at', 'paid_at', 'completed_at'
    ]
    inlines = [OrderStateLogInline, ProofUploadInline]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EscrowAccount)
class EscrowAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'status', 'amount_held', 'amount_released', 'amount_refunded']
    list_filter = ['status']
    search_fields = ['order__id']
    readonly_fields = [
        'id', 'order', 'amount_held', 'amount_released', 'amount_refunded',
        'status', 'held_at', 'released_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
