"""
URL configuration for verification app - simplified for now.
"""
from django.urls import path
from apps.verification import views

app_name = 'verification'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
]
