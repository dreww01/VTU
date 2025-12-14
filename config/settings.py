
from dotenv import load_dotenv; load_dotenv()
from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-s3_=u7_(*f7@e_b!n(*1h8tr=vnsucrqf1wuif37kjngq_r0c1'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


# ALLOWED_HOSTS = [
#     "127.0.0.1",
#     "localhost",
#     ".ngrok-free.dev",
# ]

# Allow ngrok domain
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'coalless-maurine-superaccurate.ngrok-free.dev',
]


CSRF_TRUSTED_ORIGINS = [
    "https://coalless-maurine-superaccurate.ngrok-free.dev",
    "https://*.ngrok-free.dev",  # optional, makes future ngrok URLs easier
]



# Application definition

INSTALLED_APPS = [
    "unfold",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize', 

    'accounts',
    'wallet',
    'transactions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'UTC'
TIME_ZONE = 'Africa/Lagos'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),

]


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# forget password
# Development email backend – prints email to the console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "no-reply@yourvtuapp.com"


# media
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


VTPASS_BASE_URL = os.environ.get("VTPASS_BASE_URL", "https://sandbox.vtpass.com/api")
VTPASS_API_KEY = os.environ.get("VTPASS_API_KEY")
VTPASS_SECRET_KEY = os.environ.get("VTPASS_SECRET_KEY")
VTPASS_PUBLIC_KEY = os.environ.get("VTPASS_PUBLIC_KEY")

# Email backend configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")  

# Custom email settings
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# Transaction Limits for Unverified Users
UNVERIFIED_SINGLE_LIMIT = 5000      # NGN 5,000 per transaction
UNVERIFIED_DAILY_LIMIT = 20000      # NGN 20,000 per day
UNVERIFIED_HOURLY_COUNT = 5         # 5 transactions per hour

# Transaction Limits for Verified Users (when you add KYC)
VERIFIED_SINGLE_LIMIT = 50000       # NGN 50,000 per transaction
VERIFIED_DAILY_LIMIT = 200000       # NGN 200,000 per day
VERIFIED_HOURLY_COUNT = 20          # 20 transactions per hour

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'vtp_pending_recheck.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'transactions': {  # Custom logger for the transactions app
            'handlers': ['file'],
            'level': 'INFO', 
            'propagate': True,
        },
    },
}
