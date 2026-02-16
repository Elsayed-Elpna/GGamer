"""
Dispute URL patterns.
"""
from django.urls import path
from apps.disputes import views

app_name = 'disputes'

urlpatterns = [
    # Dispute CRUD
    path('', views.DisputeListView.as_view(), name='list'),
    path('orders/<uuid:order_id>/create/', views.create_dispute, name='create'),
    path('<uuid:pk>/', views.DisputeDetailView.as_view(), name='detail'),
    
    # Evidence and messages
    path('<uuid:pk>/evidence/', views.upload_evidence, name='upload-evidence'),
    path('<uuid:pk>/messages/', views.send_message, name='send-message'),
    
    # Admin decisions
    path('<uuid:pk>/admin/refund-buyer/', views.refund_buyer, name='admin-refund-buyer'),
    path('<uuid:pk>/admin/release-seller/', views.release_seller, name='admin-release-seller'),
    path('<uuid:pk>/admin/partial-refund/', views.partial_refund, name='admin-partial-refund'),
    path('<uuid:pk>/admin/ban-seller/', views.ban_seller, name='admin-ban-seller'),
    path('<uuid:pk>/admin/close/', views.close_dispute, name='admin-close'),
]
