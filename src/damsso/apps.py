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
        Ensure DAMSSO_TENANT_MODEL has a default when it is not explicitly set.
        This covers standalone use without modifying global Django settings.
        """
        from django.conf import settings

        if not hasattr(settings, "DAMSSO_TENANT_MODEL"):
            settings.DAMSSO_TENANT_MODEL = "damsso.Tenant"

        from .admin import register_damsso_tenant_admin

        register_damsso_tenant_admin()
