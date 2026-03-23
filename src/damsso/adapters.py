"""
Custom django-allauth adapters for multi-tenant SSO support.
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import SSOProvider, TenantInvitation, TenantUser, get_tenant_model


class MultiTenantAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter that handles multi-tenant authentication.
    """

    def is_open_for_signup(self, request):
        """
        Allow signup only if user has a valid invitation, tenant signup token, or tenant allows it.
        """
        # Check if there's an invitation token in the session
        invitation_token = request.session.get("invitation_token")
        if invitation_token:
            return True

        # Check if there's a tenant signup token in the session
        tenant_signup_token = request.session.get("tenant_signup_token")
        if tenant_signup_token:
            try:
                tenant = get_tenant_model().objects.get(signup_token=tenant_signup_token, is_active=True)
                return True
            except Exception:
                pass

        # Check if tenant allows open signup (can be configured in settings)
        from django.conf import settings

        return getattr(settings, "MULTITENANT_ALLOW_OPEN_SIGNUP", False)

    def get_login_redirect_url(self, request):
        """
        Redirect to tenant-specific dashboard or default page.
        """
        # Try to get the user's primary tenant
        if request.user.is_authenticated:
            tenant_user = TenantUser.objects.filter(user=request.user, is_active=True).first()

            if tenant_user:
                # Store current tenant in session
                request.session["current_tenant_id"] = str(tenant_user.tenant.id)

                # Redirect to tenant-specific URL if configured
                from django.conf import settings

                tenant_redirect = getattr(settings, "MULTITENANT_LOGIN_REDIRECT_URL", None)
                if tenant_redirect:
                    return tenant_redirect

        return super().get_login_redirect_url(request)

    def logout(self, request):
        """
        Clear tenant session data on logout.

        This ensures tenant context is cleared even when using
        django-allauth's standard /accounts/logout/ endpoint.
        """
        # Clear tenant session data
        if "current_tenant_id" in request.session:
            del request.session["current_tenant_id"]
        if "current_tenant_slug" in request.session:
            del request.session["current_tenant_slug"]

        return super().logout(request)

    def pre_authenticate(self, request, **credentials):
        """
        Check if SSO is required for this user's tenant before password authentication.
        """
        # Only use email for authentication
        email = credentials.get("email")

        if email:
            # Check if user belongs to a tenant with enforced SSO
            tenant_user = TenantUser.objects.filter(
                user__email=email,
                is_active=True,
                tenant__sso_enabled=True,
                tenant__sso_enforced=True,
                tenant__is_active=True,
            ).first()

            if tenant_user:
                # SSO is enforced, redirect to SSO login
                messages.warning(request, _("Your organization requires Single Sign-On. Please use the SSO login."))
                # Store email for SSO flow
                request.session["sso_email"] = email
                request.session["sso_tenant_id"] = str(tenant_user.tenant.id)
                return None  # Prevent password authentication

        return super().pre_authenticate(request, **credentials)

    def save_user(self, request, user, form, commit=True):
        """
        Save user and associate with tenant if invitation or signup token exists.
        """
        user = super().save_user(request, user, form, commit=False)

        if commit:
            user.save()

            # Check for tenant signup token first
            tenant_signup_token = request.session.get("tenant_signup_token")
            if tenant_signup_token:
                try:
                    tenant = get_tenant_model().objects.get(signup_token=tenant_signup_token, is_active=True)
                    # Create tenant membership
                    TenantUser.objects.get_or_create(user=user, tenant=tenant, defaults={"role": "member"})
                    messages.success(request, _("You have successfully joined {tenant}").format(tenant=tenant.name))
                    # Clear token from session
                    del request.session["tenant_signup_token"]
                except Exception:
                    pass

            # Check for invitation (invitations take precedence if both exist)
            invitation_token = request.session.get("invitation_token")
            if invitation_token:
                from .models import TenantInvitation

                try:
                    invitation = TenantInvitation.objects.get(token=invitation_token, email=user.email)
                    if invitation.is_valid():
                        invitation.accept(user)
                        messages.success(
                            request, _("You have successfully joined {tenant}").format(tenant=invitation.tenant.name)
                        )

                        # Send acceptance notification to inviter
                        from .emails import send_invitation_accepted_notification

                        send_invitation_accepted_notification(invitation, request)

                        # Clear invitation from session
                        del request.session["invitation_token"]
                except TenantInvitation.DoesNotExist:
                    pass

        return user


class MultiTenantSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter for handling SSO providers.
    """

    def is_open_for_signup(self, request, sociallogin):
        """
        Allow social signup based on tenant configuration.
        """
        # Check if there's a tenant context
        tenant_id = request.session.get("sso_tenant_id")

        if tenant_id:
            try:
                tenant = get_tenant_model().objects.get(id=tenant_id, is_active=True)
                return tenant.sso_enabled
            except Exception:
                pass

        # Check for invitation
        invitation_token = request.session.get("invitation_token")
        if invitation_token:
            return True

        from django.conf import settings

        return getattr(settings, "MULTITENANT_ALLOW_OPEN_SIGNUP", False)

    def pre_social_login(self, request, sociallogin):
        """
        Handle user before social login is processed.

        Links existing users or creates new tenant memberships.
        """
        # If user is already logged in, we're linking accounts
        if request.user.is_authenticated:
            return

        # Get or create user from social login
        if sociallogin.is_existing:
            # User already exists, check tenant membership
            user = sociallogin.user
            tenant_id = request.session.get("sso_tenant_id")

            if tenant_id:
                try:
                    tenant = get_tenant_model().objects.get(id=tenant_id)
                    # Check if user is already a member
                    tenant_user, created = TenantUser.objects.get_or_create(
                        user=user, tenant=tenant, defaults={"role": "member"}
                    )

                    if created:
                        messages.success(request, _("Successfully joined {tenant}").format(tenant=tenant.name))
                    elif not tenant_user.is_active:
                        tenant_user.is_active = True
                        tenant_user.save()
                        messages.success(
                            request, _("Your account has been reactivated for {tenant}").format(tenant=tenant.name)
                        )

                    # Store external ID if provided
                    external_id = sociallogin.account.extra_data.get("sub") or sociallogin.account.extra_data.get("id")
                    if external_id and not tenant_user.external_id:
                        tenant_user.external_id = str(external_id)
                        tenant_user.save()

                except Exception:
                    pass

    def save_user(self, request, sociallogin, form=None):
        """
        Save user from social login and create tenant membership.
        """
        user = super().save_user(request, sociallogin, form)

        # Check for tenant context
        tenant_id = request.session.get("sso_tenant_id")
        if tenant_id:
            try:
                tenant = get_tenant_model().objects.get(id=tenant_id)
                external_id = sociallogin.account.extra_data.get("sub") or sociallogin.account.extra_data.get("id")

                TenantUser.objects.create(
                    user=user, tenant=tenant, role="member", external_id=str(external_id) if external_id else None
                )

                messages.success(request, _("Successfully joined {tenant}").format(tenant=tenant.name))
            except Exception:
                pass

        # Check for invitation
        invitation_token = request.session.get("invitation_token")
        if invitation_token:
            from .models import TenantInvitation

            try:
                invitation = TenantInvitation.objects.get(token=invitation_token, email=user.email)
                if invitation.is_valid():
                    invitation.accept(user)

                    # Send acceptance notification to inviter
                    from .emails import send_invitation_accepted_notification

                    send_invitation_accepted_notification(invitation, request)

                    del request.session["invitation_token"]
            except TenantInvitation.DoesNotExist:
                pass

        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """
        Redirect URL after successfully connecting a social account.
        """
        from django.conf import settings

        return getattr(settings, "MULTITENANT_ACCOUNT_CONNECT_REDIRECT_URL", reverse("account_connections"))
