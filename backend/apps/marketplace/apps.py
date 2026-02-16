"""
Marketplace app configuration.
Handles games, markets, and seller offers.
"""
from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.marketplace'
    verbose_name = 'Marketplace'
    
    def ready(self):
        """Import signals when app is ready."""
        # Import signals here if needed
        pass
