"""
Orders app configuration.
Handles order creation, state machine, and escrow system.
"""
from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orders'
    verbose_name = 'Orders'
    
    def ready(self):
        """Import signals when app is ready."""
        # Import signals for order state changes
        pass
