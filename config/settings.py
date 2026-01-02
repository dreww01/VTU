import os
import sys
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# CORE SETTINGS
# =============================================================================

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "SECRET_KEY environment variable is required. "
        'Generate one with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"'
    )

DEBUG = os.environ.get("DEBUG", "True") == "True"

if "test" in sys.argv:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost,.run.app").split(",")

_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "https://*.run.app")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins.split(",") if origin.strip()]

# =============================================================================
# SECURITY (Production only)
# =============================================================================

if not DEBUG and "test" not in sys.argv:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# =============================================================================
# APPS & MIDDLEWARE
# =============================================================================

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "wallet",
    "transactions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.RateLimitMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =============================================================================
# DATABASE
# =============================================================================

if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# =============================================================================
# AUTH
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

MEDIA_ROOT = BASE_DIR / "media"

if "test" in sys.argv:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
else:
    GS_BUCKET_NAME = os.environ.get("GS_BUCKET_NAME")
    if GS_BUCKET_NAME:
        GS_DEFAULT_ACL = "publicRead"
        GS_QUERYSTRING_AUTH = False
        GS_FILE_OVERWRITE = False
        STORAGES = {
            "default": {
                "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
                "OPTIONS": {"bucket_name": GS_BUCKET_NAME, "location": "media"},
            },
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
        }
        MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"
    else:
        STORAGES = {
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
        }
        MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# VTPASS API
# =============================================================================

VTPASS_BASE_URL = os.environ.get("VTPASS_BASE_URL", "https://sandbox.vtpass.com/api")
VTPASS_API_KEY = os.environ.get("VTPASS_API_KEY")
VTPASS_SECRET_KEY = os.environ.get("VTPASS_SECRET_KEY")
VTPASS_PUBLIC_KEY = os.environ.get("VTPASS_PUBLIC_KEY")

# =============================================================================
# EMAIL (Resend SMTP)
# =============================================================================

if "test" in sys.argv:
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.resend.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "resend"
    EMAIL_HOST_PASSWORD = os.getenv("RESEND_API_KEY")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Nova VTU <delivered@resend.dev>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# =============================================================================
# TRANSACTION LIMITS
# =============================================================================

# Unverified users
UNVERIFIED_SINGLE_LIMIT = 5000
UNVERIFIED_DAILY_LIMIT = 20000
UNVERIFIED_HOURLY_COUNT = 5

# Verified users (KYC)
VERIFIED_SINGLE_LIMIT = 50000
VERIFIED_DAILY_LIMIT = 200000
VERIFIED_HOURLY_COUNT = 20

# =============================================================================
# RATE LIMITING
# =============================================================================

RATELIMIT_ENABLE = "test" not in sys.argv
RATELIMIT_USE_CACHE = "default"
RATELIMIT_FAIL_OPEN = False

RATELIMIT_LOGIN = "5/m"
RATELIMIT_REGISTER = "3/m"
RATELIMIT_PASSWORD_RESET = "3/m"
RATELIMIT_API = "60/m"
RATELIMIT_PURCHASE = "10/m"
RATELIMIT_WEBHOOK = "100/m"

# =============================================================================
# UPLOAD LIMITS
# =============================================================================

DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440

# =============================================================================
# CACHE
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
        "simple": {"format": "{levelname}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple" if DEBUG else "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": True},
        "transactions": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "accounts": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "wallet": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
