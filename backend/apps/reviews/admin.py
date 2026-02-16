"""
Review admin configuration.
"""
from django.contrib import admin
from apps.reviews.models import Review, SellerRating


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'seller', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['buyer__email', 'seller__email', 'comment']
    readonly_fields = [
        'id', 'order', 'buyer', 'seller', 'rating',
        'delivery_speed', 'communication', 'as_described',
        'comment', 'ip_address', 'user_agent', 'created_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SellerRating)
class SellerRatingAdmin(admin.ModelAdmin):
    list_display = [
        'seller', 'average_rating', 'total_reviews',
        'delivery_rate', 'total_sales', 'updated_at'
    ]
    list_filter = ['updated_at']
    search_fields = ['seller__email']
    readonly_fields = [
        'id', 'seller', 'total_reviews', 'average_rating',
        'average_delivery_speed', 'average_communication', 'average_as_described',
        'five_star_count', 'four_star_count', 'three_star_count',
        'two_star_count', 'one_star_count',
        'total_sales', 'delivery_rate', 'updated_at'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
