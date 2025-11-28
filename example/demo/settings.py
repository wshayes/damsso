"""
Django settings for the multi-tenant SSO demo project.
"""

import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv  # type: ignore[import-untyped]

    load_dotenv()
except ImportError:
    # python-dotenv not installed, continue without it
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-demo-key-change-in-production")

# Model Field Encryption Key for sensitive SSO data (OIDC secrets, SAML certificates)
# SECURITY: Generate a new key for production using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# REQUIRED: This must be set in production to encrypt sensitive SSO provider fields
# SECURITY: Keep the key secure and never commit it to version control!!!
# FERNET_KEYS can be a comma-separated list in the environment variable
fernet_keys_env = os.getenv("FERNET_KEYS")
if fernet_keys_env:
    FERNET_KEYS = [key.strip() for key in fernet_keys_env.split(",") if key.strip()]
else:
    FERNET_KEYS = ["oFeOzOZYMFSV4qentv_PtDjFqnpjYBIyINo449zf2pc="]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,*").split(",")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Row Level Security (requires PostgreSQL)
    # "django_rls",  # Uncomment when using PostgreSQL
    # Allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # Multi-tenant SSO
    "django_allauth_multitenant_sso",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    # Row Level Security middleware (requires PostgreSQL and django_rls in INSTALLED_APPS)
    # "django_allauth_multitenant_sso.middleware.TenantRLSMiddleware",  # Uncomment when using PostgreSQL
]

ROOT_URLCONF = "demo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "demo.wsgi.application"

# Database
# SQLite (default - does not support Row Level Security)
# PostgreSQL (recommended for production - supports Row Level Security)
# Set DB_ENGINE=postgresql to use PostgreSQL, otherwise SQLite is used
db_engine = os.getenv("DB_ENGINE", "sqlite").lower()

if db_engine == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "multitenant_sso"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sites framework
SITE_ID = 1

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Django-allauth settings (email-only authentication)
ACCOUNT_LOGIN_METHODS = {"email"}  # Only allow email login
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]  # Only require email and passwords
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # Disable username field
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_UNIQUE_EMAIL = True  # Ensure emails are unique
ACCOUNT_ADAPTER = "django_allauth_multitenant_sso.adapters.MultiTenantAccountAdapter"
SOCIALACCOUNT_ADAPTER = "django_allauth_multitenant_sso.adapters.MultiTenantSocialAccountAdapter"

# Multi-tenant SSO settings
MULTITENANT_ALLOW_OPEN_SIGNUP = False  # Require invitations
MULTITENANT_LOGIN_REDIRECT_URL = "/"
MULTITENANT_ACCOUNT_CONNECT_REDIRECT_URL = "/accounts/connections/"

# Login/logout URLs
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Site configuration
SITE_NAME = os.getenv("SITE_NAME", "Multi-Tenant SSO Demo")
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "localhost:8000")

# Email settings (for development)
# Set EMAIL_BACKEND=smtp to use SMTP, otherwise console backend is used
email_backend = os.getenv("EMAIL_BACKEND", "console").lower()

if email_backend == "smtp":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", "server@example.com")

# Multi-tenant invitation email settings
MULTITENANT_INVITATION_FROM_EMAIL = os.getenv("MULTITENANT_INVITATION_FROM_EMAIL", "invitations@example.com")
MULTITENANT_INVITATION_REPLY_TO_INVITER = os.getenv("MULTITENANT_INVITATION_REPLY_TO_INVITER", "True").lower() in (
    "true",
    "1",
    "yes",
)  # Set reply-to as the inviter's email

# Logging configuration - suppress Chrome DevTools 404 requests
# This is a harmless Chrome DevTools request that can be safely ignored
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "suppress_chrome_devtools": {
            "()": "django.utils.log.CallbackFilter",
            "callback": lambda record: ".well-known/appspecific/com.chrome.devtools.json"
            not in str(record.getMessage()),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["suppress_chrome_devtools"],
        },
    },
    "loggers": {
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Production email settings are now configured via environment variables
# See example.env for all available settings
