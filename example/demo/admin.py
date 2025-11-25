"""
Custom admin configuration for the demo project.

This organizes the admin interface to reduce confusion between:
- Django's default User/Group models (Authentication/Authorization)
- django-allauth's EmailAddress/SocialAccount models (Accounts)
- This package's Tenant/TenantUser models (Multi-Tenant SSO)

Admin Structure:
1. Authentication/Authorization (Django):
   - Users: Base user accounts (email, password, permissions)
   - Groups: Permission groups

2. Accounts (django-allauth):
   - Email Addresses: Email management for users
   - Social Accounts: OAuth/SSO connections
   - Social Apps: OAuth provider configurations

3. Multi-Tenant SSO (this package):
   - Tenants: Organizations/companies
   - Tenant Users: User-to-tenant memberships with roles
   - SSO Providers: Per-tenant SSO configurations
   - Tenant Invitations: Invitations to join tenants

Note: TenantUsers shows users in tenant context, while Users shows all users.
For most operations, use TenantUsers to manage tenant memberships.
"""

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib import admin
from django.contrib.auth.models import Group, User

# Customize admin site headers
admin.site.site_header = "Multi-Tenant SSO Admin"
admin.site.site_title = "Multi-Tenant SSO"
admin.site.index_title = "Administration"

# Optionally hide redundant sections (uncomment if desired):
#
# Hide Django's default User/Group if you only want to manage via TenantUsers:
# admin.site.unregister(User)
# admin.site.unregister(Group)
#
# Hide django-allauth models if you only manage via tenant dashboard:
# admin.site.unregister(EmailAddress)
# admin.site.unregister(SocialAccount)
# admin.site.unregister(SocialToken)
# admin.site.unregister(SocialApp)
