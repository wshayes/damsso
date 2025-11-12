"""
App configuration for django-allauth-multitenant-sso.
"""
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AllauthMultitenantSsoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_allauth_multitenant_sso'
    verbose_name = _('Multi-Tenant SSO')

    def ready(self):
        """
        Import signal handlers when app is ready.
        """
        # Import signals here if needed
        pass
