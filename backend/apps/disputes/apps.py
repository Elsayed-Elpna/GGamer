"""
Disputes app configuration.
Handles dispute resolution and arbitration.
"""
from django.apps import AppConfig


class DisputesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.disputes'
    verbose_name = 'Disputes'
    
    def ready(self):
        """Import signals when app is ready."""
        pass
