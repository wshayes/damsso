"""
Forms for multi-tenant SSO.
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Tenant, SSOProvider, TenantInvitation, TenantUser


class TenantForm(forms.ModelForm):
    """
    Form for creating and editing tenants.
    """
    class Meta:
        model = Tenant
        fields = ['name', 'slug', 'domain', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'domain': forms.TextInput(attrs={'class': 'form-control'}),
        }


class SSOProviderForm(forms.ModelForm):
    """
    Base form for SSO provider.
    """
    class Meta:
        model = SSOProvider
        fields = ['name', 'protocol']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'protocol': forms.Select(attrs={'class': 'form-control'}),
        }


class OIDCProviderForm(forms.ModelForm):
    """
    Form for OIDC provider configuration.
    """
    class Meta:
        model = SSOProvider
        fields = [
            'name',
            'oidc_issuer',
            'oidc_client_id',
            'oidc_client_secret',
            'oidc_authorization_endpoint',
            'oidc_token_endpoint',
            'oidc_userinfo_endpoint',
            'oidc_jwks_uri',
            'oidc_scopes',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Google Workspace'
            }),
            'oidc_issuer': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://accounts.google.com'
            }),
            'oidc_client_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Client ID from your OIDC provider'
            }),
            'oidc_client_secret': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Client Secret from your OIDC provider'
            }),
            'oidc_authorization_endpoint': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Leave blank if using issuer discovery'
            }),
            'oidc_token_endpoint': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Leave blank if using issuer discovery'
            }),
            'oidc_userinfo_endpoint': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Leave blank if using issuer discovery'
            }),
            'oidc_jwks_uri': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Leave blank if using issuer discovery'
            }),
            'oidc_scopes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'openid email profile'
            }),
        }
        help_texts = {
            'oidc_issuer': _('The OIDC issuer URL. If provided, endpoints will be auto-discovered.'),
            'oidc_scopes': _('Space-separated list of OAuth scopes to request.'),
        }


class SAMLProviderForm(forms.ModelForm):
    """
    Form for SAML provider configuration.
    """
    class Meta:
        model = SSOProvider
        fields = [
            'name',
            'saml_entity_id',
            'saml_sso_url',
            'saml_slo_url',
            'saml_x509_cert',
            'saml_attribute_mapping',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Okta SAML'
            }),
            'saml_entity_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entity ID / Issuer from your SAML provider'
            }),
            'saml_sso_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'SAML SSO URL from your IdP'
            }),
            'saml_slo_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: Single Logout URL'
            }),
            'saml_x509_cert': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Paste the X.509 certificate from your SAML provider'
            }),
            'saml_attribute_mapping': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': '{"email": "email", "firstName": "first_name", "lastName": "last_name"}'
            }),
        }
        help_texts = {
            'saml_x509_cert': _('The X.509 certificate in PEM format.'),
            'saml_attribute_mapping': _('JSON mapping of SAML attributes to user fields.'),
        }


class TenantInvitationForm(forms.ModelForm):
    """
    Form for inviting users to a tenant.
    """
    class Meta:
        model = TenantInvitation
        fields = ['email', 'role']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'user@example.com'
            }),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)

        # Validate that email is not already a member
        if tenant:
            self.tenant = tenant

    def clean_email(self):
        email = self.cleaned_data['email']

        # Check if user is already a member
        if hasattr(self, 'tenant'):
            from django.contrib.auth import get_user_model
            User = get_user_model()

            try:
                user = User.objects.get(email=email)
                if TenantUser.objects.filter(user=user, tenant=self.tenant, is_active=True).exists():
                    raise forms.ValidationError(
                        _("This user is already a member of the organization.")
                    )
            except User.DoesNotExist:
                pass

            # Check if there's a pending invitation
            if TenantInvitation.objects.filter(
                tenant=self.tenant,
                email=email,
                status='pending'
            ).exists():
                raise forms.ValidationError(
                    _("There is already a pending invitation for this email.")
                )

        return email
