"""
Tests for decorators in django-allauth-multitenant-sso.
"""
import pytest
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django_allauth_multitenant_sso.decorators import (
    tenant_member_required,
    tenant_admin_required
)
from django_allauth_multitenant_sso.models import TenantUser


class TestTenantMemberRequired:
    """Tests for tenant_member_required decorator."""

    def test_allows_tenant_member(self, user, tenant, tenant_user):
        """Test decorator allows tenant member to access view."""
        @tenant_member_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{tenant.slug}/')
        request.user = user
        # Add messages middleware
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        response = test_view(request, tenant.slug)
        assert response == 'success'
        assert hasattr(request, 'tenant_user')
        assert request.tenant_user == tenant_user
        assert request.tenant == tenant

    def test_redirects_non_member(self, another_user, tenant):
        """Test decorator redirects non-member."""
        @tenant_member_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{tenant.slug}/')
        request.user = another_user
        # Add messages middleware
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        response = test_view(request, tenant.slug)
        assert response.status_code == 302
        assert '/accounts/login' in response.url

    def test_handles_inactive_tenant_user(self, user, tenant):
        """Test decorator redirects inactive tenant user."""
        # Create inactive tenant user
        TenantUser.objects.create(
            user=user,
            tenant=tenant,
            role='member',
            is_active=False
        )

        @tenant_member_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{tenant.slug}/')
        request.user = user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        response = test_view(request, tenant.slug)
        assert response.status_code == 302

    def test_handles_inactive_tenant(self, user, inactive_tenant):
        """Test decorator returns 404 for inactive tenant."""
        @tenant_member_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{inactive_tenant.slug}/')
        request.user = user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        from django.http import Http404
        with pytest.raises(Http404):
            test_view(request, inactive_tenant.slug)


class TestTenantAdminRequired:
    """Tests for tenant_admin_required decorator."""

    def test_allows_tenant_admin(self, admin_user, tenant, tenant_admin):
        """Test decorator allows tenant admin to access view."""
        @tenant_admin_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{tenant.slug}/')
        request.user = admin_user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        response = test_view(request, tenant.slug)
        assert response == 'success'
        assert hasattr(request, 'tenant_user')
        assert request.tenant_user == tenant_admin

    def test_allows_tenant_owner(self, user, tenant, tenant_owner):
        """Test decorator allows tenant owner to access view."""
        @tenant_admin_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{tenant.slug}/')
        request.user = user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        response = test_view(request, tenant.slug)
        assert response == 'success'

    def test_rejects_regular_member(self, user, tenant, tenant_user):
        """Test decorator rejects regular member."""
        @tenant_admin_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{tenant.slug}/')
        request.user = user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        response = test_view(request, tenant.slug)
        assert response.status_code == 302
        assert '/accounts/login' in response.url

    def test_rejects_non_member(self, another_user, tenant):
        """Test decorator rejects non-member."""
        @tenant_admin_required
        def test_view(request, tenant_slug):
            return 'success'

        factory = RequestFactory()
        request = factory.get(f'/tenants/{tenant.slug}/')
        request.user = another_user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        response = test_view(request, tenant.slug)
        assert response.status_code == 302
