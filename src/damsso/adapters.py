"""
django-allauth adapters for multi-tenant SSO support.

This module exposes two pairs of classes:

1. **Mixins** — ``SSORoutingAccountAdapterMixin`` and
   ``SSORoutingSocialAccountAdapterMixin`` — drop-in mixins host apps can
   combine with their own ``DefaultAccountAdapter`` / ``DefaultSocialAccountAdapter``
   subclasses without inheriting damsso's full default chain. Use these
   when you already have a custom account adapter and just want damsso's
   SSO-routing behavior.

2. **Concrete adapters** — ``MultiTenantAccountAdapter`` and
   ``MultiTenantSocialAccountAdapter`` — preconfigured combinations of the
   mixins + allauth defaults. Use these in standalone / simple setups.

Session keys
------------
The mixins store the active tenant's primary key under ``sso_tenant_pk``
in the session and read it back the same way. The legacy alias
``sso_tenant_id`` is also written and read for backwards compatibility.
If your tenant model's PK is a slug (or anything other than the default
UUID ``id``), either choice works — both keys carry whatever ``tenant.pk``
returns. The legacy key is reserved for the deprecated UUID-only path.
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models import TenantInvitation, TenantUser, get_tenant_model

SSO_TENANT_PK_SESSION_KEY = "sso_tenant_pk"
# Legacy session key; kept so existing sessions and adapters keep working.
SSO_TENANT_ID_SESSION_KEY = "sso_tenant_id"


def _store_sso_tenant(session, tenant) -> None:
    """Record the active SSO tenant's PK under both session keys."""
    session[SSO_TENANT_PK_SESSION_KEY] = str(tenant.pk)
    session[SSO_TENANT_ID_SESSION_KEY] = str(tenant.pk)


def _resolve_sso_tenant(session):
    """Resolve the SSO tenant stored in ``session``, or ``None``."""
    pk = session.get(SSO_TENANT_PK_SESSION_KEY) or session.get(SSO_TENANT_ID_SESSION_KEY)
    if not pk:
        return None
    try:
        return get_tenant_model().objects.get(pk=pk, is_active=True)
    except Exception:
        return None


class SSORoutingAccountAdapterMixin:
    """
    Mixin adding multi-tenant SSO routing to any allauth AccountAdapter.

    Subclass alongside ``DefaultAccountAdapter`` (or your own subclass)::

        from allauth.account.adapter import DefaultAccountAdapter
        from damsso.adapters import SSORoutingAccountAdapterMixin

        class MyAccountAdapter(SSORoutingAccountAdapterMixin, DefaultAccountAdapter):
            ...
    """

    def is_open_for_signup(self, request):
        # Invitation token grants signup.
        if request.session.get("invitation_token"):
            return True

        # Tenant signup token grants signup if the tenant is active.
        tenant_signup_token = request.session.get("tenant_signup_token")
        if tenant_signup_token:
            try:
                get_tenant_model().objects.get(signup_token=tenant_signup_token, is_active=True)
                return True
            except Exception:
                pass

        from django.conf import settings
        return getattr(settings, "MULTITENANT_ALLOW_OPEN_SIGNUP", False)

    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            tenant_user = TenantUser.objects.filter(user=request.user, is_active=True).first()
            if tenant_user:
                request.session["current_tenant_id"] = str(tenant_user.tenant.pk)
                from django.conf import settings
                tenant_redirect = getattr(settings, "MULTITENANT_LOGIN_REDIRECT_URL", None)
                if tenant_redirect:
                    return tenant_redirect

        return super().get_login_redirect_url(request)

    def logout(self, request):
        """Clear tenant session data on logout."""
        for key in ("current_tenant_id", "current_tenant_slug",
                    SSO_TENANT_PK_SESSION_KEY, SSO_TENANT_ID_SESSION_KEY):
            request.session.pop(key, None)
        return super().logout(request)

    def pre_authenticate(self, request, **credentials):
        """If the user's tenant enforces SSO, block password auth and stash routing context.

        Memberships with ``auth_method='local'`` are exempt — they're the
        per-membership escape hatch for users whose email domain isn't
        federated by the tenant's IdP (e.g. contractors, break-glass accounts).
        """
        email = credentials.get("email")
        if email:
            tenant_user = TenantUser.objects.filter(
                user__email=email,
                is_active=True,
                auth_method=TenantUser.AUTH_METHOD_SSO,
                tenant__sso_enabled=True,
                tenant__sso_enforced=True,
                tenant__is_active=True,
            ).first()

            if tenant_user:
                messages.warning(request, _("Your organization requires Single Sign-On. Please use the SSO login."))
                request.session["sso_email"] = email
                _store_sso_tenant(request.session, tenant_user.tenant)
                return None  # Prevent password authentication

        return super().pre_authenticate(request, **credentials)

    def save_user(self, request, user, form, commit=True):
        """Save user and consume tenant signup / invitation tokens from the session."""
        user = super().save_user(request, user, form, commit=False)

        if commit:
            user.save()

            # Tenant signup token: bare membership at the default role.
            tenant_signup_token = request.session.get("tenant_signup_token")
            if tenant_signup_token:
                try:
                    tenant = get_tenant_model().objects.get(signup_token=tenant_signup_token, is_active=True)
                    TenantUser.objects.get_or_create(user=user, tenant=tenant, defaults={"role": "member"})
                    messages.success(request, _("You have successfully joined {tenant}").format(tenant=tenant.name))
                    del request.session["tenant_signup_token"]
                except Exception:
                    pass

            # Invitations take precedence — they carry role + (optionally) auth_method.
            invitation_token = request.session.get("invitation_token")
            if invitation_token:
                try:
                    invitation = TenantInvitation.objects.get(token=invitation_token, email=user.email)
                    if invitation.is_valid():
                        invitation.accept(user)
                        messages.success(
                            request,
                            _("You have successfully joined {tenant}").format(tenant=invitation.tenant.name),
                        )
                        from .emails import send_invitation_accepted_notification
                        send_invitation_accepted_notification(invitation, request)
                        del request.session["invitation_token"]
                except TenantInvitation.DoesNotExist:
                    pass

        return user


class SSORoutingSocialAccountAdapterMixin:
    """
    Mixin adding multi-tenant SSO routing to any allauth SocialAccountAdapter.

    Subclass alongside ``DefaultSocialAccountAdapter`` (or your own subclass)::

        from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
        from damsso.adapters import SSORoutingSocialAccountAdapterMixin

        class MySocialAccountAdapter(
            SSORoutingSocialAccountAdapterMixin, DefaultSocialAccountAdapter
        ):
            ...
    """

    def is_open_for_signup(self, request, sociallogin):
        tenant = _resolve_sso_tenant(request.session)
        if tenant is not None:
            return bool(getattr(tenant, "sso_enabled", False))

        if request.session.get("invitation_token"):
            return True

        from django.conf import settings
        return getattr(settings, "MULTITENANT_ALLOW_OPEN_SIGNUP", False)

    def pre_social_login(self, request, sociallogin):
        """Link existing users to the SSO-resolved tenant."""
        if request.user.is_authenticated:
            return

        if sociallogin.is_existing:
            tenant = _resolve_sso_tenant(request.session)
            if tenant is None:
                return

            user = sociallogin.user
            tenant_user, created = TenantUser.objects.get_or_create(
                user=user, tenant=tenant, defaults={"role": "member"}
            )

            if created:
                messages.success(request, _("Successfully joined {tenant}").format(tenant=tenant.name))
            elif not tenant_user.is_active:
                tenant_user.is_active = True
                tenant_user.save()
                messages.success(
                    request,
                    _("Your account has been reactivated for {tenant}").format(tenant=tenant.name),
                )

            external_id = sociallogin.account.extra_data.get("sub") or sociallogin.account.extra_data.get("id")
            if external_id and not tenant_user.external_id:
                tenant_user.external_id = str(external_id)
                tenant_user.save()

    def save_user(self, request, sociallogin, form=None):
        """Save user from social login and create tenant membership."""
        user = super().save_user(request, sociallogin, form)

        tenant = _resolve_sso_tenant(request.session)
        if tenant is not None:
            external_id = sociallogin.account.extra_data.get("sub") or sociallogin.account.extra_data.get("id")
            TenantUser.objects.create(
                user=user,
                tenant=tenant,
                role="member",
                external_id=str(external_id) if external_id else None,
            )
            messages.success(request, _("Successfully joined {tenant}").format(tenant=tenant.name))

        invitation_token = request.session.get("invitation_token")
        if invitation_token:
            try:
                invitation = TenantInvitation.objects.get(token=invitation_token, email=user.email)
                if invitation.is_valid():
                    invitation.accept(user)
                    from .emails import send_invitation_accepted_notification
                    send_invitation_accepted_notification(invitation, request)
                    del request.session["invitation_token"]
            except TenantInvitation.DoesNotExist:
                pass

        return user

    def get_connect_redirect_url(self, request, socialaccount):
        from django.conf import settings
        return getattr(settings, "MULTITENANT_ACCOUNT_CONNECT_REDIRECT_URL", reverse("account_connections"))


class MultiTenantAccountAdapter(SSORoutingAccountAdapterMixin, DefaultAccountAdapter):
    """Standalone account adapter combining the routing mixin with allauth defaults."""


class MultiTenantSocialAccountAdapter(SSORoutingSocialAccountAdapterMixin, DefaultSocialAccountAdapter):
    """Standalone social account adapter combining the routing mixin with allauth defaults."""
