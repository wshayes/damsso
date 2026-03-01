# Docker Demo Environment

A complete demo environment with built-in OIDC and SAML identity providers powered by Keycloak.

## Quick Start

```bash
# From the project root:
just docker-up

# Or manually:
cd docker && docker compose up --build -d
```

## Services

| Service | URL | Purpose |
|---------|-----|---------|
| Django App | http://localhost:8000 | Example multi-tenant app |
| Django Admin | http://localhost:8000/admin/ | Admin interface |
| Keycloak | http://localhost:8443 | Identity Provider (OIDC + SAML) |
| Mailpit | http://localhost:8025 | Email catcher UI |

## Credentials

**Django Admin:**
- Email: `admin@demo.com`
- Password: `demo`

**Keycloak Admin:**
- Username: `admin`
- Password: `admin`

## Demo Tenants

| Tenant | Login URL | SSO Protocol | Test Users (password: `password`) |
|--------|-----------|-------------|------------|
| Acme Corp | `/tenants/login/acme-oidc/` | OIDC | alice@acme.com, bob@acme.com |
| Globex Corp | `/tenants/login/globex-saml/` | SAML 2.0 | carol@globex.com, dave@globex.com |
| Initech | `/tenants/login/initech/` | None | nouser@initech.com |

## Testing SSO Flows

### OIDC Flow (Acme Corp)

1. Visit http://localhost:8000/tenants/login/acme-oidc/
2. Click "Sign in with SSO"
3. You'll be redirected to Keycloak
4. Login as `alice@acme.com` / `password`
5. You'll be redirected back to the tenant dashboard

### SAML Flow (Globex Corp)

1. Visit http://localhost:8000/tenants/login/globex-saml/
2. Click "Sign in with SSO"
3. You'll be redirected to Keycloak
4. Login as `carol@globex.com` / `password`
5. You'll be redirected back to the tenant dashboard

### No-SSO Flow (Initech)

1. Visit http://localhost:8000/tenants/login/initech/
2. Login with `nouser@initech.com` / `password`

### Email Testing

1. Invite a user from any tenant dashboard
2. Visit http://localhost:8025 to see the invitation email

### SSO Config Management

1. Login as admin@demo.com at http://localhost:8000/admin/
2. Visit http://localhost:8000/tenants/tenant/acme-oidc/sso/
3. Click "Test Connection" to verify SSO configuration

## Just Commands

```bash
just docker-up        # Build and start all services
just docker-down      # Stop all services
just docker-logs      # Follow all service logs
just docker-logs-django  # Follow Django logs only
just docker-restart   # Restart Django (pick up code changes)
just docker-shell     # Open Django shell in container
just docker-seed      # Re-run seed command
just docker-reset     # Remove all containers and volumes
just docker-ps        # Show running containers
```

## Step-by-Step Test Plan

Use this checklist to verify the full demo environment is working correctly.

### Step 0: Start the Environment

```bash
just docker-up
```

- [ ] All 4 services start without errors
- [ ] Django logs show "Demo data seeded successfully!"
- [ ] http://localhost:8000 loads (may show login page or home page)
- [ ] http://localhost:8443 loads (Keycloak welcome page)
- [ ] http://localhost:8025 loads (Mailpit inbox)

### Step 1: Django Admin

1. Go to http://localhost:8000/admin/
2. Login with `admin@demo.com` / `demo`

- [ ] Admin dashboard loads successfully
- [ ] "Tenants" section is visible with 3 tenants (Acme Corp, Globex Corp, Initech)
- [ ] "SSO Providers" section shows 2 providers (Keycloak OIDC, Keycloak SAML)
- [ ] "Tenant Users" section shows memberships

### Step 2: OIDC SSO Flow (Acme Corp)

1. Open a **private/incognito** browser window (to avoid session conflicts with admin)
2. Go to http://localhost:8000/tenants/login/acme-oidc/
3. Click "Sign in with SSO"
4. You should be redirected to Keycloak (http://localhost:8443)
5. Login as `alice@acme.com` / `password`
6. You should be redirected back to the Django app

- [ ] Keycloak login page appears with "acme-oidc" realm branding
- [ ] After login, redirected back to tenant dashboard
- [ ] Dashboard shows you're logged in as Alice Anderson
- [ ] Dashboard shows Acme Corp tenant context

7. Log out and repeat with `bob@acme.com` / `password`

- [ ] Bob can also login via OIDC

### Step 3: SAML SSO Flow (Globex Corp)

1. Open a **new private/incognito** window
2. Go to http://localhost:8000/tenants/login/globex-saml/
3. Click "Sign in with SSO"
4. You should be redirected to Keycloak
5. Login as `carol@globex.com` / `password`
6. You should be redirected back to the Django app

- [ ] Keycloak login page appears with "globex-saml" realm branding
- [ ] After login, redirected back to tenant dashboard
- [ ] Dashboard shows you're logged in as Carol Chen
- [ ] Dashboard shows Globex Corp tenant context

7. Log out and repeat with `dave@globex.com` / `password`

- [ ] Dave can also login via SAML

### Step 4: No-SSO Flow (Initech)

1. Open a **new private/incognito** window
2. Go to http://localhost:8000/tenants/login/initech/
3. Login with `nouser@initech.com` / `password`

- [ ] No "Sign in with SSO" button (SSO not enabled)
- [ ] Password login works
- [ ] Dashboard shows Initech tenant context

### Step 5: Email / Invitations

1. Login as `admin@demo.com` / `demo` at http://localhost:8000/tenants/login/acme-oidc/
2. Navigate to the tenant dashboard
3. Click "Invite User"
4. Enter email: `newuser@test.com`, role: Member
5. Submit the invitation
6. Open http://localhost:8025 (Mailpit)

- [ ] Invitation email appears in Mailpit inbox
- [ ] Email contains an invitation link with a token
- [ ] Email shows correct tenant name and inviter

### Step 6: SSO Configuration Management

1. Login as `admin@demo.com` at http://localhost:8000/tenants/login/acme-oidc/
2. Go to http://localhost:8000/tenants/tenant/acme-oidc/sso/

- [ ] SSO configuration page loads
- [ ] Shows OIDC protocol with Keycloak endpoints
- [ ] Client ID and secret fields are populated

3. Click "Test Connection"

- [ ] Test reports success (endpoints are reachable)

### Step 7: Keycloak Admin

1. Go to http://localhost:8443
2. Click "Administration Console"
3. Login with `admin` / `admin`

- [ ] Two realms visible: `acme-oidc` and `globex-saml`
- [ ] `acme-oidc` realm has client `django-multitenant-sso` with correct redirect URIs
- [ ] `globex-saml` realm has SAML client with correct ACS URL
- [ ] Test users (alice, bob, carol, dave) are visible in their respective realms

### Step 8: Clean Restart

```bash
just docker-reset && just docker-up
```

- [ ] All volumes removed, fresh database
- [ ] All services start clean
- [ ] Demo data re-seeded successfully
- [ ] All flows from Steps 1-7 work again

## Architecture

```
Browser ──> Django App (:8000)    ──> PostgreSQL (:5432)
   │                              ──> Mailpit SMTP (:1025)
   └──> Keycloak IdP (:8443)
              │
        ┌─────┴─────┐
   realm:acme-oidc  realm:globex-saml
   (OIDC tenant)    (SAML tenant)
```

### Networking

OIDC requires that the issuer URL matches between browser and server. Since the Django container can't reach `localhost:8443`, we use **manual OIDC endpoint configuration**:

- Authorization endpoint uses `localhost:8443` (browser redirect)
- Token, userinfo, and JWKS endpoints use `keycloak:8080` (container-internal)

For SAML, all URLs go through browser redirects, so `localhost:8443` works everywhere.

## Troubleshooting

**Keycloak takes a long time to start:**
Keycloak can take 30-60 seconds to initialize. The Django container will wait for it.

**"CSRF verification failed" errors:**
Make sure `CSRF_TRUSTED_ORIGINS` includes `http://localhost:8000`. This is set automatically in docker-compose.yml.

**SAML certificate errors:**
The SAML certificate is fetched from Keycloak at seed time. If Keycloak wasn't ready, re-run: `just docker-seed`

**Port conflicts:**
Default ports: 8000 (Django), 8443 (Keycloak), 5433 (PostgreSQL), 8025/1025 (Mailpit). Change them in docker-compose.yml if needed.

**Fresh start:**
```bash
just docker-reset && just docker-up
```
