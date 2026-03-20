"""
App configuration for damsso.
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DamssoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'damsso'
    verbose_name = _('Multi-Tenant SSO')

    def ready(self):
        """
        Import signal handlers when app is ready.
        """
        # Import signals here if needed
        pass
