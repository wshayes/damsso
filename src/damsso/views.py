"""
Views for multi-tenant SSO functionality.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from .decorators import tenant_admin_required, tenant_member_required
from .emails import send_invitation_accepted_notification, send_invitation_email
from .forms import (
    OIDCProviderForm,
    SAMLProviderForm,
    SSOProtocolSelectionForm,
    SSOProviderForm,
    TenantForm,
    TenantInvitationForm,
)
from .models import SSOProvider, TenantInvitation, TenantUser, get_tenant_model
from .providers import OIDCProviderClient, SAMLProviderClient, get_provider_client

User = get_user_model()


def _get_tenant_or_404(**kwargs):
    """Shortcut: get_object_or_404 against the configured Tenant model."""
    return get_object_or_404(get_tenant_model(), **kwargs)


# ============================================================================
# Tenant Authentication Views
# ============================================================================


def tenant_login(request, tenant_slug):
    """
    Tenant-specific login page.

    Handles three scenarios:
    1. No SSO: Show email/password login form
    2. SSO Optional: Show both SSO and email/password options
    3. SSO Enforced: Redirect directly to SSO login
    """
    tenant = _get_tenant_or_404(slug=tenant_slug, is_active=True)
    sso_provider = tenant.get_active_sso_provider()

    # Scenario 3: SSO Enforced - redirect directly to SSO
    if tenant.sso_enforced and tenant.sso_enabled and sso_provider:
        return redirect("damsso:sso_login", tenant_slug=tenant_slug)

    # Handle form submission (email/password login)
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me")

        if not email or not password:
            messages.error(request, _("Please enter both email and password."))
        else:
            # Authenticate user
            user = authenticate(request, username=email, password=password)

            if user is not None:
                # Check if user is a member of this tenant
                try:
                    tenant_user = TenantUser.objects.get(user=user, tenant=tenant, is_active=True)

                    # Log the user in
                    login(request, user)

                    # Store tenant in session
                    request.session["current_tenant_id"] = str(tenant.pk)
                    request.session["current_tenant_slug"] = tenant.slug

                    # Handle remember me
                    if not remember_me:
                        request.session.set_expiry(0)  # Session expires when browser closes

                    messages.success(request, _("Welcome back, {name}!").format(name=user.get_full_name() or user.email))

                    # Redirect to tenant dashboard or next URL
                    next_url = request.GET.get("next") or reverse(
                        "damsso:tenant_dashboard", args=[tenant_slug]
                    )
                    return redirect(next_url)
                except TenantUser.DoesNotExist:
                    messages.error(
                        request,
                        _("You are not a member of this organization. Please contact your administrator."),
                    )
            else:
                messages.error(request, _("Invalid email or password."))

    # Determine which login options to show
    show_sso = tenant.sso_enabled and sso_provider and sso_provider.is_active
    show_password = not tenant.sso_enforced

    context = {
        "tenant": tenant,
        "sso_provider": sso_provider,
        "show_sso": show_sso,
        "show_password": show_password,
        "sso_only": tenant.sso_enforced and show_sso,
    }

    return render(request, "damsso/tenant_login.html", context)


def tenant_logout(request, tenant_slug):
    """
    Logout from tenant session.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug, is_active=True)

    # Log the user out
    logout(request)

    # Clear tenant session data
    if "current_tenant_id" in request.session:
        del request.session["current_tenant_id"]
    if "current_tenant_slug" in request.session:
        del request.session["current_tenant_slug"]

    messages.success(request, _("You have been logged out successfully."))

    # Redirect to tenant login page
    return redirect("damsso:tenant_login", tenant_slug=tenant_slug)


# ============================================================================
# SSO Authentication Views
# ============================================================================


def sso_login(request, tenant_slug):
    """
    Initiate SSO login for a tenant.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug, is_active=True)

    if not tenant.sso_enabled:
        messages.error(request, _("SSO is not enabled for this organization."))
        return redirect("account_login")

    sso_provider = tenant.get_active_sso_provider()
    if not sso_provider:
        messages.error(request, _("No active SSO provider configured for this organization."))
        return redirect("account_login")

    # Store tenant info in session
    request.session["sso_tenant_id"] = str(tenant.pk)

    # Route to appropriate SSO flow
    if sso_provider.protocol == "oidc":
        return _initiate_oidc_login(request, sso_provider)
    elif sso_provider.protocol == "saml":
        return _initiate_saml_login(request, sso_provider)
    else:
        messages.error(request, _("Unsupported SSO protocol."))
        return redirect("account_login")


def _initiate_oidc_login(request, sso_provider):
    """Initiate OIDC authentication flow."""
    try:
        client = OIDCProviderClient(sso_provider)
        redirect_uri = request.build_absolute_uri(
            reverse("damsso:oidc_callback", args=[sso_provider.tenant.slug])
        )

        authorization_url, state = client.get_authorization_url(request, redirect_uri)

        # Store provider ID in session (state is already stored by OIDCProviderClient)
        request.session["oidc_provider_id"] = str(sso_provider.id)

        # Mark session as modified to ensure it's saved
        request.session.modified = True

        # Debug: Log what's in the session
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"OIDC Login - Session keys after authorization: {list(request.session.keys())}")
        logger.debug(f"OIDC Login - State generated: {state}")

        return redirect(authorization_url)

    except Exception as e:
        messages.error(request, _("Failed to initiate SSO login: {error}").format(error=str(e)))
        return redirect("account_login")


def _initiate_saml_login(request, sso_provider):
    """Initiate SAML authentication flow."""
    try:
        client = SAMLProviderClient(sso_provider)
        saml_settings = client.get_saml_settings(request)

        # Prepare request data for python3-saml
        req = _prepare_saml_request(request)
        auth = OneLogin_Saml2_Auth(req, saml_settings)

        # Store provider ID in session
        request.session["saml_provider_id"] = str(sso_provider.id)

        # Redirect to IdP
        return redirect(auth.login())

    except Exception as e:
        messages.error(request, _("Failed to initiate SAML login: {error}").format(error=str(e)))
        return redirect("account_login")


def oidc_callback(request, tenant_slug):
    """
    Handle OIDC callback after authentication.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug, is_active=True)
    provider_id = request.session.get("oidc_provider_id")

    if not provider_id:
        messages.error(request, _("Invalid SSO session."))
        return redirect("account_login")

    sso_provider = get_object_or_404(SSOProvider, id=provider_id, tenant=tenant)

    # Check if we're in test mode
    is_test_mode = request.session.get("sso_test_mode", False)
    expected_email = request.session.get("sso_test_email")
    test_admin_user_id = request.session.get("sso_test_admin_user_id")
    test_tenant_slug = request.session.get("sso_test_tenant_slug")

    try:
        client = OIDCProviderClient(sso_provider)
        redirect_uri = request.build_absolute_uri(reverse("damsso:oidc_callback", args=[tenant_slug]))

        # Debug: Log session state before token exchange
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"OIDC Callback - Session keys: {list(request.session.keys())}")
        logger.debug(f"OIDC Callback - State in session: {request.session.get('oidc_state', 'NOT FOUND')}")
        logger.debug(f"OIDC Callback - State in request: {request.GET.get('state', 'NOT FOUND')}")

        # Exchange code for token
        token = client.fetch_token(request, redirect_uri)

        # Get user info
        userinfo = client.get_userinfo(token)
        actual_email = userinfo.get("email")

        # Handle test mode
        if is_test_mode and expected_email and test_admin_user_id:
            return _handle_test_mode_callback(
                request, tenant, expected_email, actual_email, test_admin_user_id, test_tenant_slug
            )

        # Normal flow: Create or update user
        user = _process_sso_user(request, sso_provider, userinfo)

        # Log user in
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        messages.success(request, _("Successfully logged in with SSO."))

        # Clean up session (state cleanup is handled in fetch_token)
        if "oidc_provider_id" in request.session:
            del request.session["oidc_provider_id"]

        return redirect(settings.LOGIN_REDIRECT_URL)

    except Exception as e:
        # Enhanced error message with debugging info
        error_msg = str(e)
        if "state" in error_msg.lower():
            # State mismatch - provide helpful debugging info
            session_keys = list(request.session.keys())
            state_in_request = request.GET.get('state', 'NOT PROVIDED')
            state_in_session = request.session.get('oidc_state', 'NOT IN SESSION')

            messages.error(
                request,
                _(
                    "SSO authentication failed: State mismatch error. "
                    "This usually means your session expired or cookies are blocked. "
                    "Please try again. (Session keys: {keys}, Request state: {req_state}...)"
                ).format(
                    keys=', '.join(session_keys[:5]),
                    req_state=state_in_request[:20] if state_in_request else 'none'
                )
            )
        else:
            messages.error(request, _("SSO authentication failed: {error}").format(error=str(e)))
        return redirect("account_login")


@csrf_exempt
@require_http_methods(["POST"])
def saml_acs(request, tenant_slug):
    """
    SAML Assertion Consumer Service (ACS) endpoint.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug, is_active=True)
    provider_id = request.session.get("saml_provider_id")

    if not provider_id:
        messages.error(request, _("Invalid SAML session."))
        return redirect("account_login")

    sso_provider = get_object_or_404(SSOProvider, id=provider_id, tenant=tenant)

    # Check if we're in test mode
    is_test_mode = request.session.get("sso_test_mode", False)
    expected_email = request.session.get("sso_test_email")
    test_admin_user_id = request.session.get("sso_test_admin_user_id")
    test_tenant_slug = request.session.get("sso_test_tenant_slug")

    try:
        client = SAMLProviderClient(sso_provider)
        saml_settings = client.get_saml_settings(request)

        req = _prepare_saml_request(request)
        auth = OneLogin_Saml2_Auth(req, saml_settings)

        # Process SAML response
        auth.process_response()
        errors = auth.get_errors()

        if errors:
            error_msg = ", ".join(errors)
            messages.error(request, _("SAML authentication failed: {error}").format(error=error_msg))
            return redirect("account_login")

        if not auth.is_authenticated():
            messages.error(request, _("SAML authentication failed."))
            return redirect("account_login")

        # Get user attributes
        attributes = auth.get_attributes()
        nameid = auth.get_nameid()

        # Convert SAML attributes to userinfo format
        userinfo = _saml_attributes_to_userinfo(attributes, nameid, sso_provider)
        actual_email = userinfo.get("email")

        # Handle test mode
        if is_test_mode and expected_email and test_admin_user_id:
            return _handle_test_mode_callback(
                request, tenant, expected_email, actual_email, test_admin_user_id, test_tenant_slug
            )

        # Normal flow: Create or update user
        user = _process_sso_user(request, sso_provider, userinfo)

        # Log user in
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        messages.success(request, _("Successfully logged in with SAML SSO."))

        # Clean up session
        if "saml_provider_id" in request.session:
            del request.session["saml_provider_id"]

        # Handle relay state
        relay_state = request.POST.get("RelayState")
        if relay_state:
            return redirect(OneLogin_Saml2_Utils.get_self_url(req) + relay_state)

        return redirect(settings.LOGIN_REDIRECT_URL)

    except Exception as e:
        messages.error(request, _("SAML authentication failed: {error}").format(error=str(e)))
        return redirect("account_login")


def saml_metadata(request, tenant_slug):
    """
    Generate SAML metadata for Service Provider.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug, is_active=True)
    sso_provider = tenant.get_active_sso_provider()

    if not sso_provider or sso_provider.protocol != "saml":
        return HttpResponse("SAML not configured", status=404)

    try:
        client = SAMLProviderClient(sso_provider)
        saml_settings = client.get_saml_settings(request)

        req = _prepare_saml_request(request)
        auth = OneLogin_Saml2_Auth(req, saml_settings)
        metadata = auth.get_settings().get_sp_metadata()

        return HttpResponse(metadata, content_type="text/xml")

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
    tenant = _get_tenant_or_404(slug=tenant_slug)
    tenant_user = get_object_or_404(TenantUser, user=request.user, tenant=tenant)

    # Handle signup token generation/regeneration
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "generate_signup_token":
            tenant.generate_signup_token()
            messages.success(request, _("Signup URL generated successfully."))
        elif action == "regenerate_signup_token":
            tenant.generate_signup_token()
            messages.success(request, _("Signup URL regenerated successfully."))
        return redirect("damsso:tenant_dashboard", tenant_slug=tenant_slug)

    context = {
        "tenant": tenant,
        "tenant_user": tenant_user,
        "member_count": tenant.tenant_users.filter(is_active=True).count(),
        "invitation_count": tenant.invitations.filter(status="pending").count(),
        "sso_provider": tenant.get_active_sso_provider(),
    }

    return render(request, "damsso/tenant_dashboard.html", context)


@login_required
@tenant_admin_required
def manage_users(request, tenant_slug):
    """
    Manage tenant users with search, filtering, and pagination.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug)

    # Get query parameters
    search_query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "")
    page_number = request.GET.get("page", 1)

    # Start with all active tenant users
    users = TenantUser.objects.filter(tenant=tenant).select_related("user").order_by("-joined_at")

    # Apply search filter (email or name)
    if search_query:
        users = users.filter(
            Q(user__email__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
        )

    # Apply role filter
    if role_filter:
        users = users.filter(role=role_filter)

    # Pagination (50 per page)
    paginator = Paginator(users, 50)
    page_obj = paginator.get_page(page_number)

    # Get role choices for filter dropdown
    role_choices = TenantUser.ROLE_CHOICES

    context = {
        "tenant": tenant,
        "page_obj": page_obj,
        "search_query": search_query,
        "role_filter": role_filter,
        "role_choices": role_choices,
        "total_count": users.count(),
    }

    # Return partial template for HTMX requests
    if request.headers.get("HX-Request"):
        return render(request, "damsso/_user_list.html", context)

    return render(request, "damsso/manage_users.html", context)


@login_required
@tenant_admin_required
def manage_sso_provider(request, tenant_slug):
    """
    Manage SSO provider for tenant.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug)
    sso_provider = tenant.sso_providers.first()

    # Handle protocol selection form submission (separate from config forms)
    if request.method == "POST" and "save_protocol_selection" in request.POST:
        if not sso_provider:
            messages.error(request, _("Please configure SSO settings before selecting a protocol."))
            return redirect("damsso:manage_sso", tenant_slug=tenant_slug)

        protocol_form = SSOProtocolSelectionForm(request.POST, instance=sso_provider)
        if protocol_form.is_valid():
            protocol_form.save()
            messages.success(request, _("Active SSO protocol updated successfully."))
            return redirect("damsso:manage_sso", tenant_slug=tenant_slug)

    # Determine which protocol configuration to show for editing
    # Priority: GET parameter > existing provider > default to OIDC
    edit_protocol = request.GET.get("protocol")
    if not edit_protocol and sso_provider:
        edit_protocol = sso_provider.protocol
    if not edit_protocol:
        edit_protocol = "oidc"

    # Validate protocol
    if edit_protocol not in ["oidc", "saml"]:
        messages.error(request, _("Invalid protocol selected."))
        return redirect("damsso:manage_sso", tenant_slug=tenant_slug)

    # Handle configuration form submission
    if request.method == "POST" and "save_configuration" in request.POST:
        if edit_protocol == "oidc":
            config_form = OIDCProviderForm(request.POST, instance=sso_provider)
        else:  # saml
            config_form = SAMLProviderForm(request.POST, instance=sso_provider)

        if config_form.is_valid():
            # Get or create the provider instance
            if sso_provider:
                provider = sso_provider
            else:
                provider = SSOProvider(tenant=tenant, protocol=edit_protocol, is_active=False)

            # Only update fields from the current protocol's form
            if edit_protocol == "oidc":
                provider.name = config_form.cleaned_data.get("name", provider.name)
                provider.oidc_issuer = config_form.cleaned_data.get("oidc_issuer") or ""
                provider.oidc_client_id = config_form.cleaned_data.get("oidc_client_id") or ""
                provider.oidc_client_secret = config_form.cleaned_data.get("oidc_client_secret") or None
                provider.oidc_authorization_endpoint = config_form.cleaned_data.get("oidc_authorization_endpoint") or ""
                provider.oidc_token_endpoint = config_form.cleaned_data.get("oidc_token_endpoint") or ""
                provider.oidc_userinfo_endpoint = config_form.cleaned_data.get("oidc_userinfo_endpoint") or ""
                provider.oidc_jwks_uri = config_form.cleaned_data.get("oidc_jwks_uri") or ""
                provider.oidc_scopes = config_form.cleaned_data.get("oidc_scopes") or "openid email profile"
            else:  # saml
                provider.name = config_form.cleaned_data.get("name", provider.name)
                provider.saml_entity_id = config_form.cleaned_data.get("saml_entity_id") or ""
                provider.saml_sso_url = config_form.cleaned_data.get("saml_sso_url") or ""
                provider.saml_slo_url = config_form.cleaned_data.get("saml_slo_url") or ""
                provider.saml_x509_cert = config_form.cleaned_data.get("saml_x509_cert") or None
                provider.saml_attribute_mapping = config_form.cleaned_data.get("saml_attribute_mapping") or {}

            provider.save()
            messages.success(request, _(f"{edit_protocol.upper()} configuration saved successfully."))
            return redirect("damsso:manage_sso", tenant_slug=tenant_slug)
    else:
        # GET request - show the forms
        if edit_protocol == "oidc":
            config_form = OIDCProviderForm(instance=sso_provider)
        else:  # saml
            config_form = SAMLProviderForm(instance=sso_provider)

    # Protocol selection form
    if sso_provider:
        protocol_form = SSOProtocolSelectionForm(instance=sso_provider)
    else:
        protocol_form = None

    # Build redirect URIs for configuration
    oidc_redirect_uri = request.build_absolute_uri(
        reverse("damsso:oidc_callback", args=[tenant_slug])
    )
    saml_acs_url = request.build_absolute_uri(reverse("damsso:saml_acs", args=[tenant.slug]))
    saml_metadata_url = request.build_absolute_uri(reverse("damsso:saml_metadata", args=[tenant.slug]))

    context = {
        "tenant": tenant,
        "sso_provider": sso_provider,
        "protocol_form": protocol_form,
        "config_form": config_form,
        "edit_protocol": edit_protocol,
        "oidc_redirect_uri": oidc_redirect_uri,
        "saml_acs_url": saml_acs_url,
        "saml_metadata_url": saml_metadata_url,
    }

    return render(request, "damsso/manage_sso.html", context)


@login_required
@tenant_admin_required
def test_sso_provider(request, tenant_slug):
    """
    Test SSO provider configuration.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug)
    sso_provider = tenant.get_active_sso_provider()

    if not sso_provider:
        messages.error(request, _("No SSO provider configured."))
        return redirect("damsso:manage_sso", tenant_slug=tenant_slug)

    if request.method == "POST":
        try:
            client = get_provider_client(sso_provider)
            test_results = client.test_connection()

            # Mark provider as tested
            sso_provider.mark_as_tested(request.user, success=test_results.get("success", False), results=test_results)

            if test_results.get("success"):
                messages.success(request, _("SSO provider test successful! You can now enable it."))
            else:
                messages.error(
                    request,
                    _("SSO provider test failed: {message}").format(
                        message=test_results.get("message", "Unknown error")
                    ),
                )

        except Exception as e:
            messages.error(request, _("Test failed: {error}").format(error=str(e)))

        return redirect("damsso:test_sso", tenant_slug=tenant_slug)

    context = {
        "tenant": tenant,
        "sso_provider": sso_provider,
    }

    return render(request, "damsso/test_sso.html", context)


@login_required
@tenant_admin_required
def test_user_sso_login(request, tenant_slug):
    """
    Test if a specific user can login via SSO and provide diagnostics.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug)
    sso_provider = tenant.get_active_sso_provider()

    test_results = None
    test_email = None

    if request.method == "POST":
        action = request.POST.get("action", "diagnose")
        test_email = request.POST.get("email", "").strip()

        if not test_email:
            messages.error(request, _("Please enter an email address to test."))
        elif action == "test_login":
            # Initiate actual SSO test login
            return _initiate_test_sso_login(request, tenant, test_email)
        else:
            # Run diagnostics
            test_results = _diagnose_user_sso_login(tenant, sso_provider, test_email)

            if test_results["can_login"]:
                messages.success(
                    request,
                    _("✅ User {email} can login via SSO").format(email=test_email),
                )
            else:
                messages.error(
                    request,
                    _("❌ User {email} cannot login via SSO - see diagnostics below").format(email=test_email),
                )

    context = {
        "tenant": tenant,
        "sso_provider": sso_provider,
        "test_results": test_results,
        "test_email": test_email,
    }

    return render(request, "damsso/test_user_sso.html", context)


def _initiate_test_sso_login(request, tenant, expected_email):
    """
    Initiate an SSO login in test mode to verify a specific user can login.
    """
    if not tenant.sso_enabled:
        messages.error(request, _("SSO is not enabled for this tenant."))
        return redirect("damsso:test_user_sso", tenant_slug=tenant.slug)

    sso_provider = tenant.get_active_sso_provider()
    if not sso_provider:
        messages.error(request, _("No active SSO provider configured."))
        return redirect("damsso:test_user_sso", tenant_slug=tenant.slug)

    # Store test mode information in session
    request.session["sso_test_mode"] = True
    request.session["sso_test_email"] = expected_email
    request.session["sso_test_admin_user_id"] = str(request.user.id)
    request.session["sso_test_tenant_slug"] = tenant.slug

    messages.info(
        request,
        _(
            "🧪 Test mode activated. You will be redirected to the SSO provider. "
            "Login with {email} to verify the configuration."
        ).format(email=expected_email),
    )

    # Redirect to standard SSO login
    return redirect("damsso:sso_login", tenant_slug=tenant.slug)


@login_required
@tenant_admin_required
def toggle_sso(request, tenant_slug):
    """
    Enable/disable SSO for tenant.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "enable":
            sso_provider = tenant.get_active_sso_provider()
            if not sso_provider or not sso_provider.is_tested:
                messages.error(request, _("Please test the SSO provider before enabling."))
            else:
                tenant.sso_enabled = True
                tenant.save()
                messages.success(request, _("SSO enabled successfully."))

        elif action == "disable":
            tenant.sso_enabled = False
            tenant.save()
            messages.success(request, _("SSO disabled successfully."))

        elif action == "enforce":
            if not tenant.sso_enabled:
                messages.error(request, _("Please enable SSO before enforcing it."))
            else:
                tenant.sso_enforced = True
                tenant.save()
                messages.warning(request, _("SSO is now enforced. Users must use SSO to log in."))

        elif action == "unenforce":
            tenant.sso_enforced = False
            tenant.save()
            messages.success(request, _("SSO enforcement disabled. Users can use password or SSO."))

    return redirect("damsso:tenant_dashboard", tenant_slug=tenant_slug)


@login_required
@tenant_admin_required
def invite_user(request, tenant_slug):
    """
    Invite user to tenant.
    """
    tenant = _get_tenant_or_404(slug=tenant_slug)

    if request.method == "POST":
        form = TenantInvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.tenant = tenant
            invitation.invited_by = request.user
            invitation.save()

            # Send invitation email
            email_sent = send_invitation_email(invitation, request)

            if email_sent:
                messages.success(request, _("Invitation sent to {email}").format(email=invitation.email))
            else:
                messages.warning(
                    request,
                    _(
                        "Invitation created for {email}, but email could not be sent. "
                        "Please check your email configuration."
                    ).format(email=invitation.email),
                )

            return redirect("damsso:tenant_dashboard", tenant_slug=tenant_slug)
    else:
        form = TenantInvitationForm()

    context = {
        "tenant": tenant,
        "form": form,
    }

    return render(request, "damsso/invite_user.html", context)


# ============================================================================
# Tenant Signup Views
# ============================================================================


def tenant_signup(request, token):
    """
    Handle tenant-specific signup with verification token.
    """
    tenant = _get_tenant_or_404(signup_token=token, is_active=True)

    # Store tenant signup token in session
    request.session["tenant_signup_token"] = token

    # If user is already logged in, add them to the tenant
    if request.user.is_authenticated:
        tenant_user, created = TenantUser.objects.get_or_create(
            user=request.user, tenant=tenant, defaults={"role": "member"}
        )
        if created:
            messages.success(request, _("You have successfully joined {tenant}!").format(tenant=tenant.name))
        else:
            messages.info(request, _("You are already a member of {tenant}.").format(tenant=tenant.name))

        # Clear token from session
        if "tenant_signup_token" in request.session:
            del request.session["tenant_signup_token"]

        return redirect("damsso:tenant_dashboard", tenant_slug=tenant.slug)

    # Otherwise, redirect to signup with tenant context
    messages.info(
        request,
        _("Sign up to join {tenant}").format(tenant=tenant.name),
    )
    return redirect("account_signup")


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
        return redirect("account_login")

    # Store invitation token in session
    request.session["invitation_token"] = token

    # If user is logged in and email matches
    if request.user.is_authenticated and request.user.email == invitation.email:
        try:
            invitation.accept(request.user)
            messages.success(request, _("You have joined {tenant}!").format(tenant=invitation.tenant.name))

            # Send acceptance notification to inviter
            send_invitation_accepted_notification(invitation, request)

            return redirect("damsso:tenant_dashboard", tenant_slug=invitation.tenant.slug)
        except Exception as e:
            messages.error(request, str(e))
            return redirect("account_login")

    # Otherwise, redirect to signup/login
    messages.info(
        request,
        _("Please sign up or log in to accept the invitation to {tenant}").format(tenant=invitation.tenant.name),
    )
    return redirect("account_signup")


# ============================================================================
# Helper Functions
# ============================================================================


def _prepare_saml_request(request):
    """
    Prepare request data for python3-saml.
    """
    return {
        "https": "on" if request.is_secure() else "off",
        "http_host": request.META["HTTP_HOST"],
        "script_name": request.META["PATH_INFO"],
        "server_port": request.META["SERVER_PORT"],
        "get_data": request.GET.copy(),
        "post_data": request.POST.copy(),
    }


def _saml_attributes_to_userinfo(attributes, nameid, sso_provider):
    """
    Convert SAML attributes to userinfo format.
    """
    mapping = sso_provider.saml_attribute_mapping or {
        "email": "email",
        "firstName": "first_name",
        "lastName": "last_name",
    }

    userinfo = {
        "sub": nameid,
        "email": nameid,  # Default to nameid
    }

    # Map attributes
    for saml_attr, user_field in mapping.items():
        if saml_attr in attributes:
            value = attributes[saml_attr]
            if isinstance(value, list) and value:
                value = value[0]
            userinfo[user_field] = value

    return userinfo


def _handle_test_mode_callback(request, tenant, expected_email, actual_email, test_admin_user_id, test_tenant_slug):
    """
    Handle SSO callback in test mode - verify email and return to test page.
    """
    # Clean up test mode session variables
    if "sso_test_mode" in request.session:
        del request.session["sso_test_mode"]
    if "sso_test_email" in request.session:
        del request.session["sso_test_email"]
    if "sso_test_admin_user_id" in request.session:
        del request.session["sso_test_admin_user_id"]
    if "sso_test_tenant_slug" in request.session:
        del request.session["sso_test_tenant_slug"]

    # Clean up other SSO session data (state cleanup is handled in fetch_token)
    for key in ["oidc_provider_id", "saml_provider_id"]:
        if key in request.session:
            del request.session[key]

    # Re-authenticate as the admin user who initiated the test
    try:
        admin_user = User.objects.get(id=test_admin_user_id)
        login(request, admin_user, backend="django.contrib.auth.backends.ModelBackend")
    except User.DoesNotExist:
        messages.error(request, _("Could not restore admin session."))
        return redirect("account_login")

    # Check if emails match
    if actual_email and actual_email.lower() == expected_email.lower():
        messages.success(
            request,
            _(
                "✅ SSO Test Successful! User {email} was able to authenticate via SSO. "
                "The email from the SSO provider matches the expected email."
            ).format(email=actual_email),
        )
    elif actual_email:
        messages.warning(
            request,
            _(
                "⚠️ SSO Test Completed with Mismatch! "
                "Expected email: {expected}, but SSO provider returned: {actual}. "
                "The user was able to authenticate, but with a different email address."
            ).format(expected=expected_email, actual=actual_email),
        )
    else:
        messages.error(
            request,
            _("❌ SSO Test Failed! The SSO provider did not return an email address."),
        )

    # Redirect back to test page
    return redirect("damsso:test_user_sso", tenant_slug=test_tenant_slug or tenant.slug)


def _process_sso_user(request, sso_provider, userinfo):
    """
    Create or update user from SSO userinfo.
    """
    email = userinfo.get("email")
    if not email:
        raise ValueError("Email is required from SSO provider")

    # Get or create user (email-only authentication)
    # Note: If User model has username field, django-allauth will handle setting it to email
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "first_name": userinfo.get("given_name", userinfo.get("first_name", "")),
            "last_name": userinfo.get("family_name", userinfo.get("last_name", "")),
        },
    )

    # Ensure username is set to email if username field exists (for Django's default User model)
    if hasattr(user, "username") and user.username != email:
        user.username = email
        user.save(update_fields=["username"])

    # Update user info if not created
    if not created:
        if userinfo.get("given_name") or userinfo.get("first_name"):
            user.first_name = userinfo.get("given_name", userinfo.get("first_name", ""))
        if userinfo.get("family_name") or userinfo.get("last_name"):
            user.last_name = userinfo.get("family_name", userinfo.get("last_name", ""))
        user.save()

    # Create or update tenant membership
    external_id = userinfo.get("sub") or userinfo.get("id")
    tenant_user, created = TenantUser.objects.get_or_create(
        user=user,
        tenant=sso_provider.tenant,
        defaults={"role": "member", "external_id": str(external_id) if external_id else None},
    )

    if not created:
        if not tenant_user.is_active:
            tenant_user.is_active = True
        if external_id and not tenant_user.external_id:
            tenant_user.external_id = str(external_id)
        tenant_user.save()

    # Store tenant in session
    request.session["current_tenant_id"] = str(sso_provider.tenant.pk)

    return user


def _diagnose_user_sso_login(tenant, sso_provider, email):
    """
    Diagnose whether a user can login via SSO and provide recommendations.

    Returns a dictionary with diagnostic information and recommendations.
    """
    import re

    checks = []
    warnings = []
    errors = []
    recommendations = []
    can_login = True

    # Basic email validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        can_login = False
        errors.append({
            "check": "Email Format",
            "status": "error",
            "message": f"Invalid email format: {email}",
            "recommendation": "Ensure the email address is correctly formatted (e.g., user@example.com)",
        })
    else:
        checks.append({
            "check": "Email Format",
            "status": "success",
            "message": f"Email format is valid: {email}",
        })

    # Check if tenant SSO is enabled
    if not tenant.sso_enabled:
        can_login = False
        errors.append({
            "check": "Tenant SSO Status",
            "status": "error",
            "message": "SSO is not enabled for this tenant",
            "recommendation": 'Enable SSO in the tenant dashboard by clicking "Enable SSO"',
        })
    else:
        checks.append({
            "check": "Tenant SSO Status",
            "status": "success",
            "message": "SSO is enabled for this tenant",
        })

    # Check if SSO provider exists and is configured
    if not sso_provider:
        can_login = False
        errors.append({
            "check": "SSO Provider",
            "status": "error",
            "message": "No SSO provider configured for this tenant",
            "recommendation": 'Configure an SSO provider in "SSO Configuration"',
        })
    else:
        checks.append({
            "check": "SSO Provider",
            "status": "success",
            "message": f"SSO provider configured: {sso_provider.name} ({sso_provider.get_protocol_display()})",
        })

        # Check if provider is active
        if not sso_provider.is_active:
            can_login = False
            errors.append({
                "check": "Provider Status",
                "status": "error",
                "message": "SSO provider is not active",
                "recommendation": "Activate the SSO provider in the configuration",
            })
        else:
            checks.append({
                "check": "Provider Status",
                "status": "success",
                "message": "SSO provider is active",
            })

        # Check if provider is tested
        if not sso_provider.is_tested:
            warnings.append({
                "check": "Provider Testing",
                "status": "warning",
                "message": "SSO provider has not been tested",
                "recommendation": 'Test the SSO provider connection using "Test SSO Connection"',
            })
        else:
            checks.append({
                "check": "Provider Testing",
                "status": "success",
                "message": f"SSO provider was tested on {sso_provider.last_tested_at.strftime('%Y-%m-%d %H:%M')}",
            })

    # Check email domain compatibility (if provider is configured)
    if sso_provider and tenant.domain:
        email_domain = email.split("@")[-1].lower()
        tenant_domain = tenant.domain.lower()

        if email_domain != tenant_domain:
            warnings.append({
                "check": "Email Domain",
                "status": "warning",
                "message": f"Email domain '{email_domain}' does not match tenant domain '{tenant_domain}'",
                "recommendation": (
                    f"Ensure the user's email domain ({email_domain}) is registered with your SSO provider. "
                    "Most SSO providers require email domains to be verified."
                ),
            })
        else:
            checks.append({
                "check": "Email Domain",
                "status": "success",
                "message": f"Email domain matches tenant domain: {tenant_domain}",
            })

    # Check if user exists locally
    try:
        user = User.objects.get(email=email)
        checks.append({
            "check": "Local User Account",
            "status": "info",
            "message": f"User account exists locally (created: {user.date_joined.strftime('%Y-%m-%d')})",
        })

        # Check if user has tenant membership
        try:
            tenant_user = TenantUser.objects.get(user=user, tenant=tenant)
            if tenant_user.is_active:
                checks.append({
                    "check": "Tenant Membership",
                    "status": "success",
                    "message": f"User is an active member of this tenant (role: {tenant_user.role})",
                })
            else:
                warnings.append({
                    "check": "Tenant Membership",
                    "status": "warning",
                    "message": "User has a tenant membership but it is inactive",
                    "recommendation": "Reactivate the user's tenant membership in the admin panel",
                })
        except TenantUser.DoesNotExist:
            checks.append({
                "check": "Tenant Membership",
                "status": "info",
                "message": "User will be automatically added to tenant upon first SSO login",
            })

    except User.DoesNotExist:
        checks.append({
            "check": "Local User Account",
            "status": "info",
            "message": "User account does not exist locally yet - will be created automatically upon first SSO login",
        })

    # Check SSO enforcement
    if tenant.sso_enforced:
        checks.append({
            "check": "SSO Enforcement",
            "status": "info",
            "message": "SSO is enforced - users must use SSO to login (password login disabled)",
        })
    else:
        checks.append({
            "check": "SSO Enforcement",
            "status": "info",
            "message": "SSO is optional - users can choose between SSO and password login",
        })

    # Generate final recommendations
    if can_login:
        recommendations.append({
            "priority": "high",
            "message": (
                f"User {email} should be able to login via SSO. "
                f"Test the login flow at: /tenants/sso/login/{tenant.slug}/"
            ),
        })
    else:
        recommendations.append({
            "priority": "high",
            "message": "Fix the errors listed above before this user can login via SSO.",
        })

    if warnings:
        recommendations.append({
            "priority": "medium",
            "message": "Address the warnings above to ensure smooth SSO operation.",
        })

    # OIDC-specific checks
    if sso_provider and sso_provider.protocol == "oidc":
        recommendations.append({
            "priority": "low",
            "message": (
                "For OIDC: Ensure the user exists in your identity provider "
                f"({sso_provider.oidc_issuer}) and their email is verified."
            ),
        })

    # SAML-specific checks
    if sso_provider and sso_provider.protocol == "saml":
        recommendations.append({
            "priority": "low",
            "message": (
                "For SAML: Ensure the user exists in your identity provider "
                f"and the email attribute mapping is correctly configured."
            ),
        })

    return {
        "can_login": can_login,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "recommendations": recommendations,
        "summary": {
            "total_checks": len(checks) + len(warnings) + len(errors),
            "passed": len([c for c in checks if c["status"] == "success"]),
            "warnings": len(warnings),
            "errors": len(errors),
        },
    }
