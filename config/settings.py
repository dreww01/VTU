import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-s3_=u7_(*f7@e_b!n(*1h8tr=vnsucrqf1wuif37kjngq_r0c1"
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True") == "True"

# Hosts configuration - load from environment in production
if "test" in sys.argv:
    ALLOWED_HOSTS = ["*"]  # Allow all hosts in tests
else:
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost,.run.app").split(",")

# CSRF trusted origins - load from environment in production
_csrf_origins = os.environ.get("CSRF_TRUSTED_ORIGINS", "https://*.run.app")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in _csrf_origins.split(",") if origin.strip()]


# =============================================================================
# SECURITY SETTINGS (Production)
# =============================================================================
# Only enable these when serving over HTTPS
if not DEBUG and "test" not in sys.argv:
    # HTTPS/SSL
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # Cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # HSTS - start with 1 hour, increase to 1 year after testing
    SECURE_HSTS_SECONDS = 3600  # 1 hour initially, set to 31536000 (1 year) later
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Other security headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# Application definition

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
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Efficient static file serving
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.RateLimitMiddleware",  # Rate limit exception handler
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Use DATABASE_URL if available (PostgreSQL), otherwise fall back to SQLite
if "test" in sys.argv:
    # Use SQLite in-memory database for tests
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


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

# TIME_ZONE = 'UTC'
TIME_ZONE = "Africa/Lagos"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # For collectstatic in production

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# WhiteNoise configuration for efficient static file serving
# Compresses and caches static files with far-future headers
# Use simpler storage for tests to avoid collectstatic requirement
if "test" in sys.argv:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    # Use GCS for media files in production if bucket name is provided
    GS_BUCKET_NAME = os.environ.get("GS_BUCKET_NAME")
    if GS_BUCKET_NAME:
        # GCS Configuration
        GS_DEFAULT_ACL = "publicRead"  # Make uploaded files publicly readable
        GS_QUERYSTRING_AUTH = False  # Don't use signed URLs for public files
        GS_FILE_OVERWRITE = False  # Don't overwrite files with same name

        STORAGES = {
            "default": {
                "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
                "OPTIONS": {
                    "bucket_name": GS_BUCKET_NAME,
                    "location": "media",  # Store in media/ folder within bucket
                },
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }
        # Update MEDIA_URL to point to GCS
        MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"
    else:
        STORAGES = {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
            },
        }


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# media
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


VTPASS_BASE_URL = os.environ.get("VTPASS_BASE_URL", "https://sandbox.vtpass.com/api")
VTPASS_API_KEY = os.environ.get("VTPASS_API_KEY")
VTPASS_SECRET_KEY = os.environ.get("VTPASS_SECRET_KEY")
VTPASS_PUBLIC_KEY = os.environ.get("VTPASS_PUBLIC_KEY")

# Email backend configuration (Resend SMTP)
# Use dummy backend for tests to prevent email sending
if "test" in sys.argv:
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = "smtp.resend.com"
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = "resend"
    EMAIL_HOST_PASSWORD = os.getenv("RESEND_API_KEY")


# Custom email settings
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Nova VTU <delivered@resend.dev>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# Transaction Limits for Unverified Users
UNVERIFIED_SINGLE_LIMIT = 5000  # NGN 5,000 per transaction
UNVERIFIED_DAILY_LIMIT = 20000  # NGN 20,000 per day
UNVERIFIED_HOURLY_COUNT = 5  # 5 transactions per hour

# Transaction Limits for Verified Users (when you add KYC)
VERIFIED_SINGLE_LIMIT = 50000  # NGN 50,000 per transaction
VERIFIED_DAILY_LIMIT = 200000  # NGN 200,000 per day
VERIFIED_HOURLY_COUNT = 20  # 20 transactions per hour

# =============================================================================
# RATE LIMITING SETTINGS
# =============================================================================
# Disable rate limiting for tests
if "test" in sys.argv:
    RATELIMIT_ENABLE = False
else:
    RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "default"
RATELIMIT_FAIL_OPEN = False  # Block if cache is unavailable (security over availability)

# Rate limit configurations (requests/period)
RATELIMIT_LOGIN = "5/m"  # 5 login attempts per minute per IP
RATELIMIT_REGISTER = "3/m"  # 3 registration attempts per minute per IP
RATELIMIT_PASSWORD_RESET = "3/m"  # 3 password reset requests per minute per IP
RATELIMIT_API = "60/m"  # 60 API requests per minute per user
RATELIMIT_PURCHASE = "10/m"  # 10 purchase attempts per minute per user
RATELIMIT_WEBHOOK = "100/m"  # 100 webhook calls per minute per IP

# =============================================================================
# DATA UPLOAD LIMITS (Protection against large payload attacks)
# =============================================================================
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB (default is 2.5MB but explicit is better)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100  # Max form fields
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB for file uploads

# =============================================================================
# CACHE CONFIGURATION (Required for rate limiting)
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple" if DEBUG else "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "transactions": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "wallet": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
