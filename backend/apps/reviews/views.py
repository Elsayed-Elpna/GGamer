"""
Review views and API endpoints.
Production-ready with fake review prevention.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.reviews.models import Review, SellerRating
from apps.reviews.serializers import (
    ReviewSerializer,
    CreateReviewSerializer,
    SellerRatingSerializer
)
from apps.reviews.services.review_service import ReviewService
from apps.orders.models import Order
from apps.accounts.models import User
from apps.verification.utils import get_client_ip


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_review(request, order_id):
    """
    Create a review for an order.
    Only buyer can review, only for CONFIRMED orders.
    """
    order = get_object_or_404(Order, id=order_id)
    
    serializer = CreateReviewSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        review = ReviewService.create_review(
            order=order,
            buyer=request.user,
            rating=serializer.validated_data['rating'],
            delivery_speed=serializer.validated_data['delivery_speed'],
            communication=serializer.validated_data['communication'],
            as_described=serializer.validated_data['as_described'],
            comment=serializer.validated_data.get('comment', ''),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        response_serializer = ReviewSerializer(review)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
def get_seller_reviews(request, seller_id):
    """
    Get reviews for a seller.
    Public endpoint.
    """
    seller = get_object_or_404(User, id=seller_id)
    
    # Get limit from query params (default 20)
    limit = int(request.query_params.get('limit', 20))
    limit = min(limit, 100)  # Max 100 reviews
    
    reviews = ReviewService.get_seller_reviews(seller, limit=limit)
    serializer = ReviewSerializer(reviews, many=True)
    
    return Response(serializer.data)


@api_view(['GET'])
def get_seller_rating(request, seller_id):
    """
    Get seller rating statistics.
    Public endpoint.
    """
    seller = get_object_or_404(User, id=seller_id)
    
    rating = ReviewService.get_seller_rating(seller)
    
    if not rating:
        return Response(
            {
                'error': 'Seller has no ratings yet',
                'seller_email': seller.email,
                'total_reviews': 0,
                'average_rating': 0.00
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = SellerRatingSerializer(rating)
    return Response(serializer.data)


class MyReviewsListView(generics.ListAPIView):
    """
    List reviews created by current user.
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Review.objects.filter(
            buyer=self.request.user
        ).select_related('order', 'seller')
