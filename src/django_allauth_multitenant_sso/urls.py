"""
URL configuration for multi-tenant SSO.
"""

from django.urls import path

from . import views

app_name = "allauth_multitenant_sso"

urlpatterns = [
    # Tenant Authentication (separate from Django accounts)
    path("login/<slug:tenant_slug>/", views.tenant_login, name="tenant_login"),
    path("logout/<slug:tenant_slug>/", views.tenant_logout, name="tenant_logout"),
    # SSO Authentication
    path("sso/login/<slug:tenant_slug>/", views.sso_login, name="sso_login"),
    path("sso/oidc/callback/<slug:tenant_slug>/", views.oidc_callback, name="oidc_callback"),
    path("sso/saml/acs/<uuid:tenant_id>/", views.saml_acs, name="saml_acs"),
    path("sso/saml/metadata/<uuid:tenant_id>/", views.saml_metadata, name="saml_metadata"),
    # Tenant Dashboard
    path("tenant/<slug:tenant_slug>/", views.tenant_dashboard, name="tenant_dashboard"),
    # SSO Management
    path("tenant/<slug:tenant_slug>/sso/", views.manage_sso_provider, name="manage_sso"),
    path("tenant/<slug:tenant_slug>/sso/test/", views.test_sso_provider, name="test_sso"),
    path("tenant/<slug:tenant_slug>/sso/test-user/", views.test_user_sso_login, name="test_user_sso"),
    path("tenant/<slug:tenant_slug>/sso/toggle/", views.toggle_sso, name="toggle_sso"),
    # User Invitations
    path("tenant/<slug:tenant_slug>/invite/", views.invite_user, name="invite_user"),
    path("invitation/<str:token>/accept/", views.accept_invitation, name="accept_invitation"),
    # User Management
    path("tenant/<slug:tenant_slug>/users/", views.manage_users, name="manage_users"),
    # Tenant Signup
    path("signup/<str:token>/", views.tenant_signup, name="tenant_signup"),
]
