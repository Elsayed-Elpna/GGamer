"""
Order URL patterns.
"""
from django.urls import path
from apps.orders import views

app_name = 'orders'

urlpatterns = [
    # Order CRUD
    path('', views.OrderListCreateView.as_view(), name='list-create'),
    path('<uuid:pk>/', views.OrderDetailView.as_view(), name='detail'),
    
    # State transitions
    path('<uuid:pk>/start/', views.start_order, name='start'),
    path('<uuid:pk>/deliver/', views.deliver_order, name='deliver'),
    path('<uuid:pk>/confirm/', views.confirm_delivery, name='confirm'),
    path('<uuid:pk>/cancel/', views.cancel_order, name='cancel'),
]
