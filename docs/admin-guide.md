# Admin Guide

This guide explains the Django admin interface structure and how to use each section effectively.

## Understanding the Admin Sections

The Django admin interface is organized into three main sections, each serving a different purpose:

### 1. Authentication/Authorization (Django Core)

This section contains Django's built-in authentication models.

#### Users
- **Purpose**: Base user accounts in the system
- **What it manages**: 
  - User email addresses
  - Passwords
  - Staff/superuser status
  - User permissions
  - Active/inactive status
- **When to use**: 
  - Creating new user accounts
  - Resetting passwords
  - Managing user permissions
  - Enabling/disabling user accounts
- **Note**: This shows ALL users in the system, regardless of tenant membership

#### Groups
- **Purpose**: Permission groups for organizing user permissions
- **What it manages**: Collections of permissions that can be assigned to users
- **When to use**: Creating reusable permission sets

### 2. Accounts (django-allauth)

This section contains django-allauth's account management models.

#### Email Addresses
- **Purpose**: Email address management for user accounts
- **What it manages**:
  - Multiple email addresses per user
  - Primary email addresses
  - Email verification status
- **When to use**: 
  - Managing user email addresses
  - Verifying email addresses manually
  - Setting primary email addresses
- **Note**: In email-only authentication mode, this is closely tied to the User model

#### Social Accounts
- **Purpose**: OAuth/SSO account connections
- **What it manages**: Links between users and external OAuth providers (Google, GitHub, etc.)
- **When to use**: Viewing which users have connected social accounts

#### Social Apps
- **Purpose**: OAuth provider configurations
- **What it manages**: Global OAuth app settings (client IDs, secrets, etc.)
- **When to use**: Configuring global OAuth providers
- **Note**: This is different from per-tenant SSO providers (see Multi-Tenant SSO section)

### 3. Multi-Tenant SSO (This Package)

This section contains the multi-tenant SSO models.

#### Tenants
- **Purpose**: Organizations or companies using the platform
- **What it manages**:
  - Tenant names, slugs, and domains
  - SSO enablement and enforcement
  - Signup tokens for public signup URLs
  - Tenant active status
- **When to use**: 
  - Creating new tenants
  - Configuring tenant settings
  - Generating signup URLs
  - Enabling/disabling tenants
- **Generating Signup Tokens**:
  - In the tenants list view, select the tenant(s)
  - Use the "Action" dropdown to select **Generate/Reset signup token**
  - Click **Go** to generate the token
  - Open the tenant to view and copy the signup URL from the **Signup Settings** section
  - **Note**: Signup tokens can only be generated via the admin action, not from the individual tenant form

#### Tenant Users
- **Purpose**: User-to-tenant memberships with role-based access
- **What it manages**:
  - Which users belong to which tenants
  - User roles within tenants (member, admin, owner)
  - External SSO identity IDs
  - Membership active status
- **When to use**: 
  - **Primary way to manage tenant memberships**
  - Adding users to tenants
  - Changing user roles within tenants
  - Viewing tenant membership history
- **Note**: This is the recommended way to manage users in a tenant context

#### SSO Providers
- **Purpose**: Per-tenant SSO configuration
- **What it manages**:
  - OIDC provider settings (issuer, client ID, secret, scopes)
  - SAML provider settings (entity ID, SSO URL, certificate, attribute mapping)
  - SSO testing status and results
- **When to use**: 
  - Configuring SSO for tenants
  - Viewing SSO test results
  - Managing SSO provider settings
- **Note**: Each tenant can have one active SSO provider

#### Tenant Invitations
- **Purpose**: Invitations for users to join tenants
- **What it manages**:
  - Invitation emails and tokens
  - Invitation status (pending, accepted, expired, cancelled)
  - Invitation expiration dates
  - Who sent the invitation
- **When to use**: 
  - Viewing invitation history
  - Resending invitations
  - Cancelling pending invitations

## Why Multiple Sections?

### Different Purposes

Each section serves a different purpose in the authentication and authorization system:

1. **Authentication/Authorization**: Core Django user management
2. **Accounts**: django-allauth's account features (email verification, social login)
3. **Multi-Tenant SSO**: Tenant-specific organization and SSO management

### Separation of Concerns

- **Users** (Authentication/Authorization): Represents a person in the system
- **Email Addresses** (Accounts): Represents email verification and management
- **Tenant Users** (Multi-Tenant SSO): Represents organization membership

A single user can:
- Have one User account (Authentication/Authorization)
- Have multiple Email Addresses (Accounts)
- Belong to multiple Tenants via Tenant Users (Multi-Tenant SSO)

## Recommended Workflow

### For Most Operations: Use Tenant Users

**For managing users in tenant context, use the Multi-Tenant SSO > Tenant Users section.**

This is the primary interface for:
- Adding users to tenants
- Changing user roles
- Viewing tenant membership
- Managing tenant-specific user data

### When to Use Each Section

#### Use Authentication/Authorization > Users when:
- Creating new user accounts
- Resetting passwords
- Managing global user permissions
- Enabling/disabling user accounts globally

#### Use Accounts > Email Addresses when:
- Managing multiple email addresses for a user
- Verifying email addresses manually
- Setting primary email addresses

#### Use Multi-Tenant SSO > Tenant Users when:
- **Adding users to tenants** (most common)
- Changing user roles within tenants
- Viewing which users belong to which tenants
- Managing tenant-specific user information

## Customizing the Admin Interface

### Hiding Redundant Sections

If you find the multiple sections confusing, you can hide some of them in your project's `admin.py`:

```python
from django.contrib import admin
from django.contrib.auth.models import User, Group
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialToken, SocialApp

# Hide Django's default User/Group if you only want to manage via TenantUsers
admin.site.unregister(User)
admin.site.unregister(Group)

# Hide django-allauth models if you only manage via tenant dashboard
admin.site.unregister(EmailAddress)
admin.site.unregister(SocialAccount)
admin.site.unregister(SocialToken)
admin.site.unregister(SocialApp)
```

**Note**: Only hide these if you're certain you won't need them. The User model is required for authentication, even if you hide it from the admin.

### Recommended Approach

Instead of hiding sections, we recommend:

1. **Use Tenant Users** as your primary interface for managing users in tenant context
2. **Use Users** only when you need to manage global account settings
3. **Use Email Addresses** only when you need to manage multiple emails per user

## Common Tasks

### Adding a User to a Tenant

1. Go to **Multi-Tenant SSO** > **Tenant Users**
2. Click **Add Tenant User**
3. Select the User and Tenant
4. Choose the Role (member, admin, or owner)
5. Save

### Creating a New User Account

1. Go to **Authentication/Authorization** > **Users**
2. Click **Add User**
3. Enter email and password
4. Set staff/superuser status if needed
5. Save
6. (Optional) Add to tenant via **Multi-Tenant SSO** > **Tenant Users**

### Viewing All Users in a Tenant

1. Go to **Multi-Tenant SSO** > **Tenant Users**
2. Use the filter dropdown to select a specific tenant
3. All users in that tenant will be displayed

### Configuring SSO for a Tenant

1. Go to **Multi-Tenant SSO** > **SSO Providers**
2. Click **Add SSO Provider**
3. Select the Tenant
4. Choose Protocol (OIDC or SAML)
5. Fill in the configuration
6. Save and test

### Generating Signup Tokens

1. Go to **Multi-Tenant SSO** > **Tenants**
2. In the list view, select the checkbox next to the tenant(s) you want to generate tokens for
3. In the "Action" dropdown at the top of the list, select **Generate/Reset signup token**
4. Click **Go** to execute the action
5. Open the tenant to view the signup URL:
   - Click on the tenant name to open the detail view
   - Scroll to the **Signup Settings** section
   - The signup URL will be displayed in a readonly input field
   - Click the input field to select and copy the URL

**Note**: Signup tokens can only be generated using the admin action in the list view. There is no button or form field to generate tokens in the individual tenant edit form.

## Best Practices

1. **Use Tenant Users for tenant operations**: This is the primary interface for tenant membership management
2. **Use Users sparingly**: Only when you need global account management
3. **Keep sections visible**: Don't hide sections unless you're certain you won't need them
4. **Use tenant dashboard for day-to-day operations**: The tenant dashboard (`/tenants/tenant/<slug>/`) provides a more user-friendly interface for tenant admins

## Summary

- **Authentication/Authorization > Users**: Base user accounts (all users)
- **Accounts > Email Addresses**: Email management (django-allauth)
- **Multi-Tenant SSO > Tenant Users**: **Primary interface for tenant membership** (recommended for most operations)

The multiple sections exist because they serve different purposes in the authentication stack. For most tenant-related operations, use the **Multi-Tenant SSO > Tenant Users** section.

