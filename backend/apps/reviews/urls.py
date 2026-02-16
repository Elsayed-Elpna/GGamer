"""
Review URL patterns.
"""
from django.urls import path
from apps.reviews import views

app_name = 'reviews'

urlpatterns = [
    # Create review
    path('orders/<uuid:order_id>/create/', views.create_review, name='create'),
    
    # My reviews
    path('my-reviews/', views.MyReviewsListView.as_view(), name='my-reviews'),
    
    # Seller reviews (public)
    path('sellers/<uuid:seller_id>/reviews/', views.get_seller_reviews, name='seller-reviews'),
    path('sellers/<uuid:seller_id>/rating/', views.get_seller_rating, name='seller-rating'),
]
