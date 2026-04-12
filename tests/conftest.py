"""
Pytest configuration and fixtures for damsso tests.
"""

import os

import django
from django.conf import settings

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
            "django.contrib.sites",
            "allauth",
            "allauth.account",
            "allauth.socialaccount",
            "damsso",
        ],
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            "allauth.account.middleware.AccountMiddleware",
        ],
        ROOT_URLCONF="tests.test_urls",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ],
                },
            }
        ],
        SITE_ID=1,
        SECRET_KEY="test-secret-key-for-testing-only",
        USE_TZ=True,
        TIME_ZONE="UTC",
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.ModelBackend",
            "allauth.account.auth_backends.AuthenticationBackend",
        ],
        # Allauth settings (email-only authentication)
        ACCOUNT_LOGIN_METHODS={"email"},
        ACCOUNT_SIGNUP_FIELDS=["email*", "password1*", "password2*"],
        ACCOUNT_USER_MODEL_USERNAME_FIELD=None,
        ACCOUNT_UNIQUE_EMAIL=True,
        ACCOUNT_ADAPTER="damsso.adapters.MultiTenantAccountAdapter",
        SOCIALACCOUNT_ADAPTER="damsso.adapters.MultiTenantSocialAccountAdapter",
        # Multi-tenant SSO settings
        MULTITENANT_ALLOW_OPEN_SIGNUP=False,
        MULTITENANT_LOGIN_REDIRECT_URL="/",
        # Email settings
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="test@example.com",
        SITE_NAME="Test Site",
        SITE_DOMAIN="testserver",
        # Fernet key for encrypted fields (test-only, not secret)
        FERNET_KEYS=["MkAi_r8OhW3RQlFcAGlF0j7pvCMKJTBLG7r8QpWJhSk="],
    )
    django.setup()

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from damsso.models import SSOProvider, Tenant, TenantInvitation, TenantUser

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    # Django's default User model requires username, so set it to email
    return User.objects.create_user(
        username="testuser@example.com", email="testuser@example.com", password="testpass123"
    )


@pytest.fixture
def another_user():
    """Create another test user."""
    # Django's default User model requires username, so set it to email
    return User.objects.create_user(
        username="anotheruser@example.com", email="anotheruser@example.com", password="testpass123"
    )


@pytest.fixture
def admin_user():
    """Create an admin user."""
    # Django's default User model requires username, so set it to email
    return User.objects.create_user(
        username="admin@example.com",
        email="admin@example.com",
        password="adminpass123",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def tenant():
    """Create a test tenant."""
    return Tenant.objects.create(name="Test Tenant", slug="test-tenant", domain="test.example.com", is_active=True)


@pytest.fixture
def another_tenant():
    """Create another test tenant."""
    return Tenant.objects.create(
        name="Another Tenant", slug="another-tenant", domain="another.example.com", is_active=True
    )


@pytest.fixture
def inactive_tenant():
    """Create an inactive tenant."""
    return Tenant.objects.create(name="Inactive Tenant", slug="inactive-tenant", is_active=False)


@pytest.fixture
def tenant_user(user, tenant):
    """Create a tenant user membership."""
    return TenantUser.objects.create(user=user, tenant=tenant, role="member")


@pytest.fixture
def tenant_admin(admin_user, tenant):
    """Create a tenant admin membership."""
    return TenantUser.objects.create(user=admin_user, tenant=tenant, role="admin")


@pytest.fixture
def tenant_owner(user, tenant):
    """Create a tenant owner membership."""
    return TenantUser.objects.create(user=user, tenant=tenant, role="owner")


@pytest.fixture
def oidc_provider(tenant):
    """Create an OIDC SSO provider."""
    return SSOProvider.objects.create(
        tenant=tenant,
        name="Test OIDC Provider",
        protocol="oidc",
        oidc_issuer="https://accounts.google.com",
        oidc_client_id="test-client-id",
        oidc_client_secret="test-client-secret",
        oidc_scopes="openid email profile",
        is_active=True,
    )


@pytest.fixture
def saml_provider(tenant):
    """Create a SAML SSO provider."""
    return SSOProvider.objects.create(
        tenant=tenant,
        name="Test SAML Provider",
        protocol="saml",
        saml_entity_id="https://idp.example.com",
        saml_sso_url="https://idp.example.com/sso",
        saml_x509_cert="-----BEGIN CERTIFICATE-----\nMIIDEzCCAfugAwIBAgIJAKoSdj...\n-----END CERTIFICATE-----",
        saml_attribute_mapping={"email": "email", "firstName": "first_name", "lastName": "last_name"},
        is_active=True,
    )


@pytest.fixture
def invitation(user, tenant):
    """Create a tenant invitation."""
    return TenantInvitation.objects.create(
        tenant=tenant, email="invited@example.com", role="member", invited_by=user, status="pending"
    )


@pytest.fixture
def expired_invitation(user, tenant):
    """Create an expired invitation."""
    invitation = TenantInvitation.objects.create(
        tenant=tenant, email="expired@example.com", role="member", invited_by=user, status="pending"
    )
    invitation.expires_at = timezone.now() - timedelta(days=1)
    invitation.save()
    return invitation


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass
