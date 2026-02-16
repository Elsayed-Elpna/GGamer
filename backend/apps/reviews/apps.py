"""
Reviews app configuration.
Handles buyer ratings and seller reputation.
"""
from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reviews'
    verbose_name = 'Reviews'
    
    def ready(self):
        """Import signals when app is ready."""
        pass
