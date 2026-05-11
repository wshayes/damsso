# Host-App Integration

This guide covers everything you need to drop damsso into an existing
Django project — one that already has its own tenant / organization model,
admin, RLS conventions, and account-adapter customizations.

The smaller standalone path (use damsso's bundled `Tenant`, get every
default) is covered in the [Quick Start](quickstart.md). This page is for
the *swap-mode* path: keep your tenant model, keep your invitation flow,
keep your RLS conventions, and let damsso plug in alongside them.

## TL;DR checklist

1. Inherit `damsso.models.TenantSSOMixin` on your tenant model.
2. Set `DAMSSO_TENANT_MODEL = "myapp.MyTenant"`.
3. Set `FERNET_KEYS = [...]` for SSO secret encryption.
4. Compose `SSORoutingAccountAdapterMixin` into your own
   `DefaultAccountAdapter` subclass (and the social equivalent).
5. If your tenant migration must finish before damsso's FK columns are
   created, set `DAMSSO_EXTRA_MIGRATION_DEPENDENCIES`.
6. If you manage RLS yourself, set `DAMSSO_ENABLE_RLS = False` (or
   override the bypass predicate).
7. If you ship your own invitation model, set
   `DAMSSO_USE_BUILTIN_INVITATIONS = False`.

Everything else (URLs, views, templates) works as documented in the
standalone Quick Start.

## 1. Swap the tenant model

Add the mixin to your tenant model so damsso can read the SSO flags
(`sso_enabled`, `sso_enforced`, etc.):

```python
# myapp/models.py
from django.db import models
from damsso.models import TenantSSOMixin

class Tenant(TenantSSOMixin, models.Model):
    slug = models.SlugField(primary_key=True, max_length=63)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    # ...your own fields...
```

```python
# settings.py
DAMSSO_TENANT_MODEL = "myapp.Tenant"
```

`damsso.models.get_tenant_model()` will now resolve to your model
everywhere, and damsso's migrations will skip the bundled `damsso.Tenant`
CreateModel / AlterField operations.

### PK type considerations

damsso supports any PK type your tenant model uses. Internally, damsso
stores the tenant under `request.session["sso_tenant_pk"]` as a string and
re-resolves via `tenant_model.objects.get(pk=...)`. UUID PKs and slug PKs
both work without further configuration.

## 2. Encryption keys

damsso encrypts SSO client secrets and SAML certificates at rest using
Fernet. Provide one or more keys via:

```python
# settings.py
FERNET_KEYS = [
    os.environ["FERNET_KEY"],         # current key
    # os.environ["FERNET_KEY_OLD"],   # prior key during rotation
]
```

The first key is used for encryption; remaining keys are tried for
decryption (in order) to allow zero-downtime rotation.

## 3. Adapters — use the mixin

If you already maintain a custom `AccountAdapter` (which is common in
existing host apps), you don't need to inherit damsso's
`MultiTenantAccountAdapter` outright. Compose just the routing behavior:

```python
# myapp/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from damsso.adapters import (
    SSORoutingAccountAdapterMixin,
    SSORoutingSocialAccountAdapterMixin,
)


class MyAccountAdapter(SSORoutingAccountAdapterMixin, DefaultAccountAdapter):
    """Combines damsso SSO routing with the host's own account logic."""

    def get_email_confirmation_url(self, request, emailconfirmation):
        # ... host overrides ...
        return super().get_email_confirmation_url(request, emailconfirmation)


class MySocialAccountAdapter(SSORoutingSocialAccountAdapterMixin, DefaultSocialAccountAdapter):
    pass
```

```python
# settings.py
ACCOUNT_ADAPTER = "myapp.adapters.MyAccountAdapter"
SOCIALACCOUNT_ADAPTER = "myapp.adapters.MySocialAccountAdapter"
```

The mixin is responsible for:

- Blocking password auth when `tenant.sso_enforced` is true.
- Stashing the active SSO tenant under `sso_tenant_pk` in the session.
- Resolving the SSO tenant during social signup.
- Honoring `invitation_token` and `tenant_signup_token` session keys.

If you'd rather replace the whole flow, write your own adapter from
scratch — damsso doesn't require the mixin to function, but it saves you
from re-implementing the SSO routing pieces.

## 4. Migration ordering

When your tenant model's schema changes need to land *before* damsso adds
FK columns referencing it, inject ordering constraints via:

```python
# settings.py
DAMSSO_EXTRA_MIGRATION_DEPENDENCIES = {
    # damsso.0001_initial waits for myapp's tenant table to be finalized
    "0001_initial": [("myapp", "0002_my_tenant_pk_change")],
    "0003_setup_rls": [("myapp", "0002_my_tenant_pk_change")],
}
```

Keys are damsso migration filenames without the `.py` extension; values
are lists of `(app_label, migration_name)` tuples that get appended to
the migration's `dependencies` list. The migrations that support this
hook today are `0001_initial` and `0003_setup_rls`.

You do not need to set this if damsso's `swappable_dependency()` already
gives you the right order — that's the case when your tenant model's
migration that creates the tenant table is the only one that matters.

## 5. Row Level Security

damsso ships a migration (`0003_setup_rls`) that creates per-table RLS
policies on `damsso_tenantuser`, `damsso_ssoprovider`, and
`damsso_tenantinvitation`. The default policy is:

```sql
USING (
    tenant_id::text = current_setting('rls.tenant_id', true)
    OR current_setting('rls.tenant_id', true) IS NULL
);
```

Two host-side overrides are available:

### Disable damsso's RLS migration

If your project applies RLS via its own migrations / signals, skip
damsso's:

```python
# settings.py
DAMSSO_ENABLE_RLS = False
```

The migration record still applies (so subsequent damsso migrations can
depend on it), but the migration is a no-op.

### Override the admin-bypass predicate

If your project uses a different convention for the admin-bypass check
(for example, an empty string instead of `NULL`), override the SQL
fragment:

```python
# settings.py
DAMSSO_RLS_BYPASS_PREDICATE = "current_setting('rls.tenant_id', true) = ''"
```

This SQL fragment is injected into damsso's policy in place of the
default `current_setting('rls.tenant_id', true) IS NULL`. Make sure
your application code and other migrations follow the same convention.

## 6. Invitations

damsso ships a bundled `TenantInvitation` model and admin. The model
still exists in swap mode (the table is created), but you may not want
the admin entry to appear if your project has its own invitation flow:

```python
# settings.py
DAMSSO_USE_BUILTIN_INVITATIONS = False
```

When False, damsso skips registering `TenantInvitationAdmin`. You
don't need to call `admin.site.unregister(TenantInvitation)`.

If you keep the bundled flow (the default), damsso's `MultiTenantAccountAdapter`
will read `invitation_token` from the session during signup and call
`TenantInvitation.accept()` automatically.

## 7. Mounting URLs and middleware

The URL include is the same as standalone:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    path("sso/", include("damsso.urls")),
    # ...
]
```

If your project has a tenant-resolution middleware that requires a tenant
context, exempt damsso's URLs from it — login screens and SSO callbacks
must be reachable without a tenant first being set in the request.

## 8. Tenant lifecycle hooks

damsso lets you plug into the SSO user lifecycle without monkeypatching:

```python
# settings.py
DAMSSO_SSO_USER_POLICY = "myapp.sso_hooks.deny_unless_invited"
DAMSSO_POST_SSO_USER = "myapp.sso_hooks.sync_user_tenant_attr"
```

Both are dotted paths.

- `DAMSSO_SSO_USER_POLICY(request, tenant, email, userinfo) -> None` —
  raise `ValueError` to block the login (damsso renders an error page).
- `DAMSSO_POST_SSO_USER(request, user, tenant, sso_provider) -> None` —
  runs after `TenantUser` is synced; use this to set a `User.tenant`
  pointer, push to a profile service, or emit analytics.

## Reference: settings introduced in this guide

| Setting | Default | Purpose |
| --- | --- | --- |
| `DAMSSO_TENANT_MODEL` | `"damsso.Tenant"` | Dotted path to your concrete tenant model |
| `FERNET_KEYS` | — (required) | Keys used to encrypt SSO secrets at rest |
| `DAMSSO_EXTRA_MIGRATION_DEPENDENCIES` | `{}` | Inject extra migration deps per damsso migration name |
| `DAMSSO_ENABLE_RLS` | `True` | Set False to make `0003_setup_rls` a no-op |
| `DAMSSO_RLS_BYPASS_PREDICATE` | `current_setting('rls.tenant_id', true) IS NULL` | Override the admin-bypass SQL fragment |
| `DAMSSO_USE_BUILTIN_INVITATIONS` | `True` | Set False to hide damsso's `TenantInvitation` admin |
| `DAMSSO_SSO_USER_POLICY` | `None` | Dotted path: deny SSO logins by raising `ValueError` |
| `DAMSSO_POST_SSO_USER` | `None` | Dotted path: post-SSO callback for user sync |
| `DAMSSO_OIDC_HTTP_TIMEOUT` | `15` | Seconds; OIDC metadata/JWKS/token/userinfo HTTP timeout |
