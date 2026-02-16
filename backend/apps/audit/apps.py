"""
Audit app configuration.
Handles central audit logging for the entire system.
"""
from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = 'Audit & Logging'
    
    def ready(self):
        """Import signals when app is ready."""
        pass
