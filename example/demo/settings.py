"""
Django settings for the multi-tenant SSO demo project.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-demo-key-change-in-production"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

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
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# PostgreSQL (recommended for production - supports Row Level Security)
# Uncomment the configuration below and comment out SQLite to use PostgreSQL with RLS:
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": "multitenant_sso",
#         "USER": "postgres",
#         "PASSWORD": "your_password",
#         "HOST": "localhost",
#         "PORT": "5432",
#     }
# }

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
SITE_NAME = "Multi-Tenant SSO Demo"
SITE_DOMAIN = "localhost:8000"

# Email settings (for development)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@example.com"
SERVER_EMAIL = "server@example.com"

# Multi-tenant invitation email settings
MULTITENANT_INVITATION_FROM_EMAIL = "invitations@example.com"
MULTITENANT_INVITATION_REPLY_TO_INVITER = True  # Set reply-to as the inviter's email

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

# Production email settings (uncomment and configure for production)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'  # or your SMTP server
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'
# DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
# MULTITENANT_INVITATION_FROM_EMAIL = 'invitations@yourdomain.com'
