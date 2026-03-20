# Multi-Tenant SSO Demo Project

This is a demonstration Django project showing how to use `damsso`.

## Setup

### Environment Variables

This project uses environment variables for sensitive configuration. Before running the project:

1. Copy the example environment file:
```bash
cd example
cp example.env .env
```

2. Edit `.env` and update the values as needed:
   - **SECRET_KEY**: Generate a new Django secret key for production
   - **FERNET_KEYS**: Generate encryption keys for SSO data (required in production)
   - **DEBUG**: Set to `False` in production
   - **Database settings**: Configure if using PostgreSQL
   - **Email settings**: Configure for production email delivery

**Security:** Never commit the `.env` file to version control!

### Quick Setup with Just (Recommended)

If you have [just](https://github.com/casey/just) installed, you can use:

```bash
# From the project root
just example-setup          # Uses uv (required)

# Create a superuser
just example-createsuperuser

# Start the development server
just dev
```

**Note:** This project uses [uv](https://github.com/astral-sh/uv) exclusively for package management. See [AGENTS.md](../AGENTS.md) for details.

### Manual Setup

1. Install dependencies:
```bash
cd example
uv pip install -e ..
uv pip install django django-allauth python3-saml authlib cryptography python-dotenv
```

2. Run migrations:
```bash
python manage.py migrate
```

3. Create a superuser:
```bash
python manage.py createsuperuser
```

4. Run the development server:
```bash
python manage.py runserver
```

## Usage

### 1. Create a Tenant

Access the Django admin at http://localhost:8000/admin/ and create a new Tenant:
- Name: Your Organization
- Slug: your-org
- Domain: example.com (optional)

### 2. Create a Tenant Admin User

Create a TenantUser record linking your superuser account to the tenant with role "admin" or "owner".

### 3. Configure SSO

Visit http://localhost:8000/tenants/tenant/your-org/sso/ to configure an SSO provider.

#### For OIDC (e.g., Google):
- Name: Google Workspace
- Protocol: OIDC
- Issuer: https://accounts.google.com
- Client ID: (from Google Cloud Console)
- Client Secret: (from Google Cloud Console)
- Scopes: openid email profile

#### For SAML (e.g., Okta):
- Name: Okta SAML
- Protocol: SAML
- Entity ID: (from Okta)
- SSO URL: (from Okta)
- X.509 Certificate: (from Okta)

### 4. Test SSO Configuration

Visit http://localhost:8000/tenants/tenant/your-org/sso/test/ to test the SSO configuration.

### 5. Enable SSO

Once tested, enable SSO for your tenant at http://localhost:8000/tenants/tenant/your-org/

### 6. SSO Login

Users can now log in via SSO at: http://localhost:8000/tenants/sso/login/your-org/

## Features Demonstrated

- Multi-tenant organization management
- OIDC and SAML SSO configuration
- SSO testing functionality for tenant admins
- User invitation system
- Optional SSO enforcement (disable password login)
- Integration with django-allauth for authentication

## Directory Structure

```
example/
├── manage.py           # Django management script
├── example.env         # Example environment variables (copy to .env)
├── .env                # Environment variables (create from example.env, not in git)
├── demo/              # Main Django project
│   ├── settings.py    # Project settings
│   ├── urls.py        # URL configuration
│   ├── wsgi.py        # WSGI entry point
│   └── asgi.py        # ASGI entry point
└── README.md          # This file
```
