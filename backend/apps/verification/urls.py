"""
URL configuration for verification app.
"""
from django.urls import path
from apps.verification import views

app_name = 'verification'

urlpatterns = [
    # Phone verification endpoints
    path('phone/send-otp/', views.send_otp, name='send_otp'),
    path('phone/verify-otp/', views.verify_otp, name='verify_otp'),
    path('phone/status/', views.phone_verification_status, name='phone_status'),
    
    # Seller verification endpoints
    path('seller/submit/', views.submit_seller_verification, name='submit_seller_verification'),
    path('seller/status/', views.seller_verification_status, name='seller_status'),
    path('seller/can-create-offers/', views.can_create_offers, name='can_create_offers'),
    
    # Admin endpoints
    path('admin/pending/', views.list_pending_verifications, name='list_pending'),
    path('admin/<int:verification_id>/', views.verification_details, name='verification_details'),
    path('admin/<int:verification_id>/approve/', views.approve_verification, name='approve_verification'),
    path('admin/<int:verification_id>/reject/', views.reject_verification, name='reject_verification'),
]
