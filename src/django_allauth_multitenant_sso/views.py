"""
Views for multi-tenant SSO functionality.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import login, get_user_model
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from .models import Tenant, TenantUser, SSOProvider, TenantInvitation
from .providers import get_provider_client, OIDCProviderClient, SAMLProviderClient
from .decorators import tenant_admin_required, tenant_member_required
from .forms import (
    SSOProviderForm, OIDCProviderForm, SAMLProviderForm,
    TenantInvitationForm, TenantForm
)
from .emails import send_invitation_email, send_invitation_accepted_notification

User = get_user_model()


# ============================================================================
# SSO Authentication Views
# ============================================================================

def sso_login(request, tenant_slug):
    """
    Initiate SSO login for a tenant.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)

    if not tenant.sso_enabled:
        messages.error(request, _("SSO is not enabled for this organization."))
        return redirect('account_login')

    sso_provider = tenant.get_active_sso_provider()
    if not sso_provider:
        messages.error(request, _("No active SSO provider configured for this organization."))
        return redirect('account_login')

    # Store tenant info in session
    request.session['sso_tenant_id'] = str(tenant.id)

    # Route to appropriate SSO flow
    if sso_provider.protocol == 'oidc':
        return _initiate_oidc_login(request, sso_provider)
    elif sso_provider.protocol == 'saml':
        return _initiate_saml_login(request, sso_provider)
    else:
        messages.error(request, _("Unsupported SSO protocol."))
        return redirect('account_login')


def _initiate_oidc_login(request, sso_provider):
    """Initiate OIDC authentication flow."""
    try:
        client = OIDCProviderClient(sso_provider)
        redirect_uri = request.build_absolute_uri(
            reverse('allauth_multitenant_sso:oidc_callback', args=[sso_provider.tenant.slug])
        )

        authorization_url, state = client.get_authorization_url(request, redirect_uri)

        # Store state in session
        request.session['oidc_state'] = state
        request.session['oidc_provider_id'] = str(sso_provider.id)

        return redirect(authorization_url)

    except Exception as e:
        messages.error(request, _("Failed to initiate SSO login: {error}").format(error=str(e)))
        return redirect('account_login')


def _initiate_saml_login(request, sso_provider):
    """Initiate SAML authentication flow."""
    try:
        client = SAMLProviderClient(sso_provider)
        saml_settings = client.get_saml_settings(request)

        # Prepare request data for python3-saml
        req = _prepare_saml_request(request)
        auth = OneLogin_Saml2_Auth(req, saml_settings)

        # Store provider ID in session
        request.session['saml_provider_id'] = str(sso_provider.id)

        # Redirect to IdP
        return redirect(auth.login())

    except Exception as e:
        messages.error(request, _("Failed to initiate SAML login: {error}").format(error=str(e)))
        return redirect('account_login')


def oidc_callback(request, tenant_slug):
    """
    Handle OIDC callback after authentication.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug, is_active=True)
    provider_id = request.session.get('oidc_provider_id')

    if not provider_id:
        messages.error(request, _("Invalid SSO session."))
        return redirect('account_login')

    sso_provider = get_object_or_404(SSOProvider, id=provider_id, tenant=tenant)

    try:
        client = OIDCProviderClient(sso_provider)
        redirect_uri = request.build_absolute_uri(
            reverse('allauth_multitenant_sso:oidc_callback', args=[tenant_slug])
        )

        # Exchange code for token
        token = client.fetch_token(request, redirect_uri)

        # Get user info
        userinfo = client.get_userinfo(token)

        # Create or update user
        user = _process_sso_user(request, sso_provider, userinfo)

        # Log user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        messages.success(request, _("Successfully logged in with SSO."))

        # Clean up session
        if 'oidc_state' in request.session:
            del request.session['oidc_state']
        if 'oidc_provider_id' in request.session:
            del request.session['oidc_provider_id']

        return redirect(settings.LOGIN_REDIRECT_URL)

    except Exception as e:
        messages.error(request, _("SSO authentication failed: {error}").format(error=str(e)))
        return redirect('account_login')


@csrf_exempt
@require_http_methods(["POST"])
def saml_acs(request, tenant_id):
    """
    SAML Assertion Consumer Service (ACS) endpoint.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id, is_active=True)
    provider_id = request.session.get('saml_provider_id')

    if not provider_id:
        messages.error(request, _("Invalid SAML session."))
        return redirect('account_login')

    sso_provider = get_object_or_404(SSOProvider, id=provider_id, tenant=tenant)

    try:
        client = SAMLProviderClient(sso_provider)
        saml_settings = client.get_saml_settings(request)

        req = _prepare_saml_request(request)
        auth = OneLogin_Saml2_Auth(req, saml_settings)

        # Process SAML response
        auth.process_response()
        errors = auth.get_errors()

        if errors:
            error_msg = ', '.join(errors)
            messages.error(request, _("SAML authentication failed: {error}").format(error=error_msg))
            return redirect('account_login')

        if not auth.is_authenticated():
            messages.error(request, _("SAML authentication failed."))
            return redirect('account_login')

        # Get user attributes
        attributes = auth.get_attributes()
        nameid = auth.get_nameid()

        # Convert SAML attributes to userinfo format
        userinfo = _saml_attributes_to_userinfo(attributes, nameid, sso_provider)

        # Create or update user
        user = _process_sso_user(request, sso_provider, userinfo)

        # Log user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        messages.success(request, _("Successfully logged in with SAML SSO."))

        # Clean up session
        if 'saml_provider_id' in request.session:
            del request.session['saml_provider_id']

        # Handle relay state
        relay_state = request.POST.get('RelayState')
        if relay_state:
            return redirect(OneLogin_Saml2_Utils.get_self_url(req) + relay_state)

        return redirect(settings.LOGIN_REDIRECT_URL)

    except Exception as e:
        messages.error(request, _("SAML authentication failed: {error}").format(error=str(e)))
        return redirect('account_login')


def saml_metadata(request, tenant_id):
    """
    Generate SAML metadata for Service Provider.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id, is_active=True)
    sso_provider = tenant.get_active_sso_provider()

    if not sso_provider or sso_provider.protocol != 'saml':
        return HttpResponse("SAML not configured", status=404)

    try:
        client = SAMLProviderClient(sso_provider)
        saml_settings = client.get_saml_settings(request)

        req = _prepare_saml_request(request)
        auth = OneLogin_Saml2_Auth(req, saml_settings)
        metadata = auth.get_settings().get_sp_metadata()

        return HttpResponse(metadata, content_type='text/xml')

    except Exception as e:
        return HttpResponse(f"Error generating metadata: {str(e)}", status=500)


# ============================================================================
# Tenant Admin Views
# ============================================================================

@login_required
@tenant_admin_required
def tenant_dashboard(request, tenant_slug):
    """
    Tenant admin dashboard.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    tenant_user = get_object_or_404(TenantUser, user=request.user, tenant=tenant)

    context = {
        'tenant': tenant,
        'tenant_user': tenant_user,
        'member_count': tenant.tenant_users.filter(is_active=True).count(),
        'invitation_count': tenant.invitations.filter(status='pending').count(),
        'sso_provider': tenant.get_active_sso_provider(),
    }

    return render(request, 'allauth_multitenant_sso/tenant_dashboard.html', context)


@login_required
@tenant_admin_required
def manage_sso_provider(request, tenant_slug):
    """
    Manage SSO provider for tenant.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    sso_provider = tenant.get_active_sso_provider()

    if request.method == 'POST':
        protocol = request.POST.get('protocol')

        if protocol == 'oidc':
            form = OIDCProviderForm(request.POST, instance=sso_provider)
        elif protocol == 'saml':
            form = SAMLProviderForm(request.POST, instance=sso_provider)
        else:
            form = SSOProviderForm(request.POST, instance=sso_provider)

        if form.is_valid():
            provider = form.save(commit=False)
            provider.tenant = tenant
            provider.protocol = protocol
            provider.save()

            messages.success(request, _("SSO provider saved successfully."))
            return redirect('allauth_multitenant_sso:test_sso', tenant_slug=tenant_slug)
    else:
        if sso_provider:
            if sso_provider.protocol == 'oidc':
                form = OIDCProviderForm(instance=sso_provider)
            else:
                form = SAMLProviderForm(instance=sso_provider)
        else:
            form = SSOProviderForm()

    context = {
        'tenant': tenant,
        'sso_provider': sso_provider,
        'form': form,
    }

    return render(request, 'allauth_multitenant_sso/manage_sso.html', context)


@login_required
@tenant_admin_required
def test_sso_provider(request, tenant_slug):
    """
    Test SSO provider configuration.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    sso_provider = tenant.get_active_sso_provider()

    if not sso_provider:
        messages.error(request, _("No SSO provider configured."))
        return redirect('allauth_multitenant_sso:manage_sso', tenant_slug=tenant_slug)

    if request.method == 'POST':
        try:
            client = get_provider_client(sso_provider)
            test_results = client.test_connection()

            # Mark provider as tested
            sso_provider.mark_as_tested(
                request.user,
                success=test_results.get('success', False),
                results=test_results
            )

            if test_results.get('success'):
                messages.success(request, _("SSO provider test successful! You can now enable it."))
            else:
                messages.error(
                    request,
                    _("SSO provider test failed: {message}").format(
                        message=test_results.get('message', 'Unknown error')
                    )
                )

        except Exception as e:
            messages.error(request, _("Test failed: {error}").format(error=str(e)))

        return redirect('allauth_multitenant_sso:test_sso', tenant_slug=tenant_slug)

    context = {
        'tenant': tenant,
        'sso_provider': sso_provider,
    }

    return render(request, 'allauth_multitenant_sso/test_sso.html', context)


@login_required
@tenant_admin_required
def toggle_sso(request, tenant_slug):
    """
    Enable/disable SSO for tenant.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'enable':
            sso_provider = tenant.get_active_sso_provider()
            if not sso_provider or not sso_provider.is_tested:
                messages.error(request, _("Please test the SSO provider before enabling."))
            else:
                tenant.sso_enabled = True
                tenant.save()
                messages.success(request, _("SSO enabled successfully."))

        elif action == 'disable':
            tenant.sso_enabled = False
            tenant.save()
            messages.success(request, _("SSO disabled successfully."))

        elif action == 'enforce':
            if not tenant.sso_enabled:
                messages.error(request, _("Please enable SSO before enforcing it."))
            else:
                tenant.sso_enforced = True
                tenant.save()
                messages.warning(
                    request,
                    _("SSO is now enforced. Users must use SSO to log in.")
                )

        elif action == 'unenforce':
            tenant.sso_enforced = False
            tenant.save()
            messages.success(request, _("SSO enforcement disabled. Users can use password or SSO."))

    return redirect('allauth_multitenant_sso:tenant_dashboard', tenant_slug=tenant_slug)


@login_required
@tenant_admin_required
def invite_user(request, tenant_slug):
    """
    Invite user to tenant.
    """
    tenant = get_object_or_404(Tenant, slug=tenant_slug)

    if request.method == 'POST':
        form = TenantInvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.tenant = tenant
            invitation.invited_by = request.user
            invitation.save()

            # Send invitation email
            email_sent = send_invitation_email(invitation, request)

            if email_sent:
                messages.success(
                    request,
                    _("Invitation sent to {email}").format(email=invitation.email)
                )
            else:
                messages.warning(
                    request,
                    _("Invitation created for {email}, but email could not be sent. "
                      "Please check your email configuration.").format(email=invitation.email)
                )

            return redirect('allauth_multitenant_sso:tenant_dashboard', tenant_slug=tenant_slug)
    else:
        form = TenantInvitationForm()

    context = {
        'tenant': tenant,
        'form': form,
    }

    return render(request, 'allauth_multitenant_sso/invite_user.html', context)


# ============================================================================
# Invitation Views
# ============================================================================

def accept_invitation(request, token):
    """
    Accept tenant invitation.
    """
    invitation = get_object_or_404(TenantInvitation, token=token)

    if not invitation.is_valid():
        messages.error(request, _("This invitation has expired or is no longer valid."))
        return redirect('account_login')

    # Store invitation token in session
    request.session['invitation_token'] = token

    # If user is logged in and email matches
    if request.user.is_authenticated and request.user.email == invitation.email:
        try:
            invitation.accept(request.user)
            messages.success(
                request,
                _("You have joined {tenant}!").format(tenant=invitation.tenant.name)
            )

            # Send acceptance notification to inviter
            send_invitation_accepted_notification(invitation, request)

            return redirect('allauth_multitenant_sso:tenant_dashboard',
                          tenant_slug=invitation.tenant.slug)
        except Exception as e:
            messages.error(request, str(e))
            return redirect('account_login')

    # Otherwise, redirect to signup/login
    messages.info(
        request,
        _("Please sign up or log in to accept the invitation to {tenant}").format(
            tenant=invitation.tenant.name
        )
    )
    return redirect('account_signup')


# ============================================================================
# Helper Functions
# ============================================================================

def _prepare_saml_request(request):
    """
    Prepare request data for python3-saml.
    """
    return {
        'https': 'on' if request.is_secure() else 'off',
        'http_host': request.META['HTTP_HOST'],
        'script_name': request.META['PATH_INFO'],
        'server_port': request.META['SERVER_PORT'],
        'get_data': request.GET.copy(),
        'post_data': request.POST.copy(),
    }


def _saml_attributes_to_userinfo(attributes, nameid, sso_provider):
    """
    Convert SAML attributes to userinfo format.
    """
    mapping = sso_provider.saml_attribute_mapping or {
        'email': 'email',
        'firstName': 'first_name',
        'lastName': 'last_name',
    }

    userinfo = {
        'sub': nameid,
        'email': nameid,  # Default to nameid
    }

    # Map attributes
    for saml_attr, user_field in mapping.items():
        if saml_attr in attributes:
            value = attributes[saml_attr]
            if isinstance(value, list) and value:
                value = value[0]
            userinfo[user_field] = value

    return userinfo


def _process_sso_user(request, sso_provider, userinfo):
    """
    Create or update user from SSO userinfo.
    """
    email = userinfo.get('email')
    if not email:
        raise ValueError("Email is required from SSO provider")

    # Get or create user
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': email,
            'first_name': userinfo.get('given_name', userinfo.get('first_name', '')),
            'last_name': userinfo.get('family_name', userinfo.get('last_name', '')),
        }
    )

    # Update user info if not created
    if not created:
        if userinfo.get('given_name') or userinfo.get('first_name'):
            user.first_name = userinfo.get('given_name', userinfo.get('first_name', ''))
        if userinfo.get('family_name') or userinfo.get('last_name'):
            user.last_name = userinfo.get('family_name', userinfo.get('last_name', ''))
        user.save()

    # Create or update tenant membership
    external_id = userinfo.get('sub') or userinfo.get('id')
    tenant_user, created = TenantUser.objects.get_or_create(
        user=user,
        tenant=sso_provider.tenant,
        defaults={
            'role': 'member',
            'external_id': str(external_id) if external_id else None
        }
    )

    if not created:
        if not tenant_user.is_active:
            tenant_user.is_active = True
        if external_id and not tenant_user.external_id:
            tenant_user.external_id = str(external_id)
        tenant_user.save()

    # Store tenant in session
    request.session['current_tenant_id'] = str(sso_provider.tenant.id)

    return user
