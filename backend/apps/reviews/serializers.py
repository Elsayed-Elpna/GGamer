"""
Review serializers.
"""
from rest_framework import serializers
from apps.reviews.models import Review, SellerRating


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviews."""
    buyer_email = serializers.EmailField(source='buyer.email', read_only=True)
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    order_id = serializers.UUIDField(source='order.id', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'order_id', 'buyer_email', 'seller_email',
            'rating', 'delivery_speed', 'communication', 'as_described',
            'comment', 'created_at'
        ]
        read_only_fields = fields


class CreateReviewSerializer(serializers.Serializer):
    """Serializer for creating reviews."""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    delivery_speed = serializers.IntegerField(min_value=1, max_value=5)
    communication = serializers.IntegerField(min_value=1, max_value=5)
    as_described = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True
    )


class SellerRatingSerializer(serializers.ModelSerializer):
    """Serializer for seller rating statistics."""
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    delivery_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
        source='delivery_rate'
    )
    
    class Meta:
        model = SellerRating
        fields = [
            'id', 'seller_email', 'total_reviews', 'average_rating',
            'average_delivery_speed', 'average_communication', 'average_as_described',
            'five_star_count', 'four_star_count', 'three_star_count',
            'two_star_count', 'one_star_count',
            'total_sales', 'delivery_percentage', 'updated_at'
        ]
        read_only_fields = fields
