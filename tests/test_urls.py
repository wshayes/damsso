"""
Minimal URL configuration for tests.
"""
from django.urls import path, include

urlpatterns = [
    path('accounts/', include('allauth.urls')),
    path('tenants/', include('django_allauth_multitenant_sso.urls')),
]
