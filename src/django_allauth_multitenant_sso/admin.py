"""
Admin interface for multi-tenant SSO models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import Tenant, TenantUser, SSOProvider, TenantInvitation


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'domain', 'sso_enabled', 'sso_enforced', 'is_active', 'created_at']
    list_filter = ['is_active', 'sso_enabled', 'sso_enforced', 'created_at']
    search_fields = ['name', 'slug', 'domain']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'slug', 'domain', 'is_active')
        }),
        (_('SSO Settings'), {
            'fields': ('sso_enabled', 'sso_enforced')
        }),
        (_('Metadata'), {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'tenant', 'role', 'is_active', 'external_id', 'joined_at']
    list_filter = ['role', 'is_active', 'tenant', 'joined_at']
    search_fields = ['user__email', 'tenant__name', 'external_id']
    readonly_fields = ['id', 'joined_at']
    autocomplete_fields = ['user', 'tenant']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = _('User Email')
    user_email.admin_order_field = 'user__email'


@admin.register(SSOProvider)
class SSOProviderAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tenant', 'protocol', 'is_active', 'is_tested',
        'status_indicator', 'last_tested_at', 'created_at'
    ]
    list_filter = ['protocol', 'is_active', 'is_tested', 'created_at']
    search_fields = ['name', 'tenant__name', 'oidc_client_id', 'saml_entity_id']
    readonly_fields = ['id', 'is_tested', 'last_tested_at', 'last_tested_by', 'test_results', 'created_at', 'updated_at']
    autocomplete_fields = ['tenant']

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'name', 'protocol', 'is_active')
        }),
        (_('OIDC Configuration'), {
            'fields': (
                'oidc_issuer', 'oidc_client_id', 'oidc_client_secret',
                'oidc_authorization_endpoint', 'oidc_token_endpoint',
                'oidc_userinfo_endpoint', 'oidc_jwks_uri', 'oidc_scopes'
            ),
            'classes': ('collapse',)
        }),
        (_('SAML Configuration'), {
            'fields': (
                'saml_entity_id', 'saml_sso_url', 'saml_slo_url',
                'saml_x509_cert', 'saml_attribute_mapping'
            ),
            'classes': ('collapse',)
        }),
        (_('Testing Information'), {
            'fields': ('is_tested', 'last_tested_at', 'last_tested_by', 'test_results'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_indicator(self, obj):
        if obj.is_active and obj.is_tested:
            color = 'green'
            text = 'Active & Tested'
        elif obj.is_active:
            color = 'orange'
            text = 'Active (Not Tested)'
        elif obj.is_tested:
            color = 'blue'
            text = 'Inactive (Tested)'
        else:
            color = 'red'
            text = 'Inactive'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    status_indicator.short_description = _('Status')


@admin.register(TenantInvitation)
class TenantInvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'tenant', 'role', 'status', 'invited_by', 'created_at', 'expires_at']
    list_filter = ['status', 'role', 'created_at', 'expires_at']
    search_fields = ['email', 'tenant__name', 'invited_by__email']
    readonly_fields = ['id', 'token', 'created_at', 'accepted_at']
    autocomplete_fields = ['tenant', 'invited_by']

    fieldsets = (
        (None, {
            'fields': ('id', 'tenant', 'email', 'role', 'invited_by')
        }),
        (_('Status'), {
            'fields': ('status', 'token', 'expires_at', 'accepted_at')
        }),
        (_('Timestamps'), {
            'fields': ('created_at',)
        }),
    )
