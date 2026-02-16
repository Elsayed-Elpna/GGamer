"""
Chat URL patterns.
"""
from django.urls import path
from apps.chat import views

app_name = 'chat'

urlpatterns = [
    # Chat room operations
    path('orders/<uuid:order_id>/', views.get_order_chat, name='get-chat'),
    path('orders/<uuid:order_id>/messages/', views.get_chat_messages, name='get-messages'),
    path('orders/<uuid:order_id>/send/', views.send_message, name='send-message'),
    
    # Admin operations
    path('orders/<uuid:order_id>/add-support/', views.add_support_to_chat, name='add-support'),
]
