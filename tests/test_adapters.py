"""
Tests for adapters in damsso.
"""

from unittest.mock import Mock, patch

import pytest
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from damsso.adapters import MultiTenantAccountAdapter, MultiTenantSocialAccountAdapter
from damsso.models import TenantInvitation, TenantUser

User = get_user_model()


class TestMultiTenantAccountAdapter:
    """Tests for MultiTenantAccountAdapter."""

    def test_is_open_for_signup_with_invitation(self, invitation):
        """Test signup is allowed with valid invitation token."""
        adapter = MultiTenantAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session["invitation_token"] = invitation.token
        request.session.save()

        assert adapter.is_open_for_signup(request) is True

    def test_is_open_for_signup_without_invitation(self):
        """Test signup is not allowed without invitation (default)."""
        adapter = MultiTenantAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()

        assert adapter.is_open_for_signup(request) is False

    @pytest.mark.django_db
    def test_is_open_for_signup_with_setting(self, settings):
        """Test signup allowed when MULTITENANT_ALLOW_OPEN_SIGNUP is True."""
        settings.MULTITENANT_ALLOW_OPEN_SIGNUP = True

        adapter = MultiTenantAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()

        assert adapter.is_open_for_signup(request) is True

    def test_get_login_redirect_url_with_tenant(self, user, tenant_user):
        """Test login redirect with tenant membership."""
        adapter = MultiTenantAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")
        request.user = user

        # Add session middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()

        redirect_url = adapter.get_login_redirect_url(request)

        # Should store tenant ID in session
        assert "current_tenant_id" in request.session
        assert request.session["current_tenant_id"] == str(tenant_user.tenant.id)

    def test_save_user_with_invitation(self, invitation):
        """Test user save with invitation accepts invitation."""
        adapter = MultiTenantAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session and messages
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session["invitation_token"] = invitation.token
        request.session.save()

        setattr(request, "_messages", FallbackStorage(request))

        # Create user with matching email (username set to email for Django's default User model)
        user = User(username=invitation.email, email=invitation.email)

        # Create a proper form mock with cleaned_data
        form = Mock()
        form.cleaned_data = {
            "email": invitation.email,
            "password1": "testpass123",
        }

        saved_user = adapter.save_user(request, user, form, commit=True)

        # Refresh invitation
        invitation.refresh_from_db()

        assert saved_user.email == invitation.email
        assert invitation.status == "accepted"
        assert TenantUser.objects.filter(user=saved_user, tenant=invitation.tenant).exists()


class TestMultiTenantSocialAccountAdapter:
    """Tests for MultiTenantSocialAccountAdapter."""

    def test_is_open_for_signup_with_tenant_sso(self, tenant):
        """Test social signup allowed with tenant SSO enabled."""
        tenant.sso_enabled = True
        tenant.save()

        adapter = MultiTenantSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session["sso_tenant_id"] = str(tenant.id)
        request.session.save()

        sociallogin = Mock()
        assert adapter.is_open_for_signup(request, sociallogin) is True

    def test_is_open_for_signup_with_invitation(self, invitation):
        """Test social signup allowed with invitation."""
        adapter = MultiTenantSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session["invitation_token"] = invitation.token
        request.session.save()

        sociallogin = Mock()
        assert adapter.is_open_for_signup(request, sociallogin) is True

    def test_pre_social_login_creates_tenant_membership(self, user, tenant):
        """Test pre_social_login creates tenant membership for existing user."""
        adapter = MultiTenantSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")
        request.user = Mock()
        request.user.is_authenticated = False

        # Add session and messages
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session["sso_tenant_id"] = str(tenant.id)
        request.session.save()

        setattr(request, "_messages", FallbackStorage(request))

        # Mock social login
        sociallogin = Mock()
        sociallogin.is_existing = True
        sociallogin.user = user
        sociallogin.account = Mock()
        sociallogin.account.extra_data = {"sub": "external-123"}

        adapter.pre_social_login(request, sociallogin)

        # Should create tenant membership
        assert TenantUser.objects.filter(user=user, tenant=tenant).exists()

        tenant_user = TenantUser.objects.get(user=user, tenant=tenant)
        assert tenant_user.external_id == "external-123"

    def test_save_user_creates_tenant_membership(self, tenant):
        """Test save_user creates tenant membership."""
        adapter = MultiTenantSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session and messages
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session["sso_tenant_id"] = str(tenant.id)
        request.session.save()

        setattr(request, "_messages", FallbackStorage(request))

        # Mock social login
        sociallogin = Mock()
        sociallogin.account = Mock()
        sociallogin.account.extra_data = {"sub": "external-456", "email": "social@example.com"}

        # Mock the parent save_user to return a user
        with patch("allauth.socialaccount.adapter.DefaultSocialAccountAdapter.save_user") as mock_save:
            user = User.objects.create_user(
                username="social@example.com", email="social@example.com", password="pass123"
            )
            mock_save.return_value = user

            saved_user = adapter.save_user(request, sociallogin, form=None)

            # Should create tenant membership
            assert TenantUser.objects.filter(user=saved_user, tenant=tenant, external_id="external-456").exists()

    def test_save_user_with_invitation(self, invitation):
        """Test save_user with invitation."""
        adapter = MultiTenantSocialAccountAdapter()
        factory = RequestFactory()
        request = factory.get("/")

        # Add session and messages
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session["invitation_token"] = invitation.token
        request.session.save()

        setattr(request, "_messages", FallbackStorage(request))

        # Mock social login
        sociallogin = Mock()
        sociallogin.account = Mock()
        sociallogin.account.extra_data = {"email": invitation.email}

        # Mock the parent save_user to return a user
        with patch("allauth.socialaccount.adapter.DefaultSocialAccountAdapter.save_user") as mock_save:
            user = User.objects.create_user(username=invitation.email, email=invitation.email, password="pass123")
            mock_save.return_value = user

            adapter.save_user(request, sociallogin, form=None)

            # Refresh invitation
            invitation.refresh_from_db()

            assert invitation.status == "accepted"
            assert TenantUser.objects.filter(user=user, tenant=invitation.tenant).exists()
