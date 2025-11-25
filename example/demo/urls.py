"""
URL configuration for demo project.
"""

from django.contrib import admin
from django.urls import include, path

# Import custom admin configuration
from . import admin as custom_admin  # noqa: F401
from .views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("tenants/", include("django_allauth_multitenant_sso.urls")),
    path("", HomeView.as_view(), name="home"),
]
