"""
Pytest configuration and fixtures for django-allauth-multitenant-sso tests.
"""
import os
import django
from django.conf import settings

# Configure Django settings for testing
if not settings.configured:
    settings.configure(
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'django.contrib.sites',
            'allauth',
            'allauth.account',
            'allauth.socialaccount',
            'django_allauth_multitenant_sso',
        ],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            'allauth.account.middleware.AccountMiddleware',
        ],
        ROOT_URLCONF='tests.test_urls',
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': True,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                ],
            },
        }],
        SITE_ID=1,
        SECRET_KEY='test-secret-key-for-testing-only',
        USE_TZ=True,
        TIME_ZONE='UTC',
        AUTHENTICATION_BACKENDS=[
            'django.contrib.auth.backends.ModelBackend',
            'allauth.account.auth_backends.AuthenticationBackend',
        ],
        # Allauth settings
        ACCOUNT_AUTHENTICATION_METHOD='email',
        ACCOUNT_EMAIL_REQUIRED=True,
        ACCOUNT_USERNAME_REQUIRED=False,
        ACCOUNT_ADAPTER='django_allauth_multitenant_sso.adapters.MultiTenantAccountAdapter',
        SOCIALACCOUNT_ADAPTER='django_allauth_multitenant_sso.adapters.MultiTenantSocialAccountAdapter',
        # Multi-tenant SSO settings
        MULTITENANT_ALLOW_OPEN_SIGNUP=False,
        MULTITENANT_LOGIN_REDIRECT_URL='/',
        # Email settings
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='test@example.com',
        SITE_NAME='Test Site',
        SITE_DOMAIN='testserver',
    )
    django.setup()

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django_allauth_multitenant_sso.models import (
    Tenant, TenantUser, SSOProvider, TenantInvitation
)

User = get_user_model()


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='testpass123'
    )


@pytest.fixture
def another_user():
    """Create another test user."""
    return User.objects.create_user(
        username='anotheruser',
        email='anotheruser@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='adminpass123',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def tenant():
    """Create a test tenant."""
    return Tenant.objects.create(
        name='Test Tenant',
        slug='test-tenant',
        domain='test.example.com',
        is_active=True
    )


@pytest.fixture
def another_tenant():
    """Create another test tenant."""
    return Tenant.objects.create(
        name='Another Tenant',
        slug='another-tenant',
        domain='another.example.com',
        is_active=True
    )


@pytest.fixture
def inactive_tenant():
    """Create an inactive tenant."""
    return Tenant.objects.create(
        name='Inactive Tenant',
        slug='inactive-tenant',
        is_active=False
    )


@pytest.fixture
def tenant_user(user, tenant):
    """Create a tenant user membership."""
    return TenantUser.objects.create(
        user=user,
        tenant=tenant,
        role='member'
    )


@pytest.fixture
def tenant_admin(admin_user, tenant):
    """Create a tenant admin membership."""
    return TenantUser.objects.create(
        user=admin_user,
        tenant=tenant,
        role='admin'
    )


@pytest.fixture
def tenant_owner(user, tenant):
    """Create a tenant owner membership."""
    return TenantUser.objects.create(
        user=user,
        tenant=tenant,
        role='owner'
    )


@pytest.fixture
def oidc_provider(tenant):
    """Create an OIDC SSO provider."""
    return SSOProvider.objects.create(
        tenant=tenant,
        name='Test OIDC Provider',
        protocol='oidc',
        oidc_issuer='https://accounts.google.com',
        oidc_client_id='test-client-id',
        oidc_client_secret='test-client-secret',
        oidc_scopes='openid email profile',
        is_active=True
    )


@pytest.fixture
def saml_provider(tenant):
    """Create a SAML SSO provider."""
    return SSOProvider.objects.create(
        tenant=tenant,
        name='Test SAML Provider',
        protocol='saml',
        saml_entity_id='https://idp.example.com',
        saml_sso_url='https://idp.example.com/sso',
        saml_x509_cert='-----BEGIN CERTIFICATE-----\nMIIDEzCCAfugAwIBAgIJAKoSdj...\n-----END CERTIFICATE-----',
        saml_attribute_mapping={
            'email': 'email',
            'firstName': 'first_name',
            'lastName': 'last_name'
        },
        is_active=True
    )


@pytest.fixture
def invitation(user, tenant):
    """Create a tenant invitation."""
    return TenantInvitation.objects.create(
        tenant=tenant,
        email='invited@example.com',
        role='member',
        invited_by=user,
        status='pending'
    )


@pytest.fixture
def expired_invitation(user, tenant):
    """Create an expired invitation."""
    invitation = TenantInvitation.objects.create(
        tenant=tenant,
        email='expired@example.com',
        role='member',
        invited_by=user,
        status='pending'
    )
    invitation.expires_at = timezone.now() - timedelta(days=1)
    invitation.save()
    return invitation


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass
