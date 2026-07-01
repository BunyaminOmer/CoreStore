"""
Django settings for corelogic project.
"""

import os
from pathlib import Path
from typing import List, Optional

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if it exists
load_dotenv(os.path.join(BASE_DIR, '.env'))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name: str, default: int = 0) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be an integer.') from exc


def env_float(name: str, default: float = 0) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == '':
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f'{name} must be a number.') from exc


def env_list(name: str) -> List[str]:
    value = os.environ.get(name, '')
    return [item.strip() for item in value.split(',') if item.strip()]


def clean_host(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    host = value.strip().removeprefix('https://').removeprefix('http://')
    return host.strip('/').split('/')[0] or None


# SECURITY WARNING: keep the secret key used in production secret!
DEBUG = env_bool('DEBUG', default=False)

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-local-development-only-change-me'
    else:
        raise ImproperlyConfigured('SECRET_KEY must be set when DEBUG=False.')

# GoDaddy / custom domain. Use the plain domain only, e.g. example.com.
DOMAIN = clean_host(os.environ.get('DOMAIN'))
CUSTOM_DOMAIN_HOSTS = []
if DOMAIN:
    CUSTOM_DOMAIN_HOSTS.append(DOMAIN)
    if DOMAIN.startswith('www.'):
        CUSTOM_DOMAIN_HOSTS.append(DOMAIN.removeprefix('www.'))
    else:
        CUSTOM_DOMAIN_HOSTS.append(f'www.{DOMAIN}')

PLATFORM_HOSTS = [
    '.onrender.com',
    '.up.railway.app',
    '.vercel.app',
]

render_hostname = clean_host(os.environ.get('RENDER_EXTERNAL_HOSTNAME'))
if render_hostname:
    PLATFORM_HOSTS.append(render_hostname)

LOCAL_HOSTS = ['localhost', '127.0.0.1', '[::1]']
if DEBUG:
    ALLOWED_HOSTS = LOCAL_HOSTS + CUSTOM_DOMAIN_HOSTS + env_list('ALLOWED_HOSTS')
else:
    ALLOWED_HOSTS = CUSTOM_DOMAIN_HOSTS + PLATFORM_HOSTS + env_list('ALLOWED_HOSTS')

ALLOWED_HOSTS = list(dict.fromkeys(host for host in ALLOWED_HOSTS if host))

CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')
for host in CUSTOM_DOMAIN_HOSTS:
    CSRF_TRUSTED_ORIGINS.append(f'https://{host}')
CSRF_TRUSTED_ORIGINS.extend([
    'https://*.onrender.com',
    'https://*.up.railway.app',
    'https://*.vercel.app',
])
CSRF_TRUSTED_ORIGINS = list(dict.fromkeys(CSRF_TRUSTED_ORIGINS))

# Production security. Render terminates TLS before requests reach Django.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=not DEBUG)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', default=not DEBUG)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', default=not DEBUG)
SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', default=0 if DEBUG else 3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
REFERRER_POLICY = 'same-origin'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Cloudinary Storage
    'cloudinary_storage',
    'cloudinary',

    # Third party
    'crispy_forms',
    'crispy_bootstrap5',
    # Local apps
    'accounts',
    'store',
    'vendors',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corelogic.middleware.CanonicalHostRedirectMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'corelogic.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart_context',
                'store.context_processors.categories_context',
                'store.context_processors.notifications_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'corelogic.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DEBUG and not DATABASE_URL:
    raise ImproperlyConfigured('DATABASE_URL must be set when DEBUG=False.')

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'tr'

TIME_ZONE = 'Europe/Istanbul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Whitenoise Compression & Caching for Production
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Cloudinary Configuration (required for uploaded media in production)
CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME')
CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY')
CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET')
cloudinary_values = [CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]
REQUIRE_CLOUDINARY = env_bool('REQUIRE_CLOUDINARY', default=not DEBUG)

if all(cloudinary_values):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
elif any(cloudinary_values):
    raise ImproperlyConfigured(
        'CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET '
        'must be set together.'
    )
elif REQUIRE_CLOUDINARY:
    raise ImproperlyConfigured(
        'Cloudinary credentials must be set when REQUIRE_CLOUDINARY=True.'
    )


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'


# Authentication redirects
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


# Email / Brevo SMTP. Keep credentials in environment variables, never in git.
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.locmem.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp-relay.brevo.com')
EMAIL_PORT = env_int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', default=True)
EMAIL_TIMEOUT = env_int('EMAIL_TIMEOUT', default=10)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'CoreLogic Store <noreply@corelogic.store>')
ADMIN_NOTIFICATION_EMAIL = os.environ.get('ADMIN_NOTIFICATION_EMAIL', DEFAULT_FROM_EMAIL)
EMAIL_2FA_SHOW_DEBUG_CODE = env_bool(
    'EMAIL_2FA_SHOW_DEBUG_CODE',
    default=DEBUG and EMAIL_BACKEND.endswith('locmem.EmailBackend'),
)

# Gemini / OpenAI gerçek LLM destek entegrasyonu. API anahtarları ortam değişkeninde kalmalı.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_SUPPORT_MODEL = os.environ.get('GEMINI_SUPPORT_MODEL', 'gemini-3.5-flash')
GEMINI_SUPPORT_TIMEOUT = env_int('GEMINI_SUPPORT_TIMEOUT', default=12)
GEMINI_SUPPORT_MAX_OUTPUT_TOKENS = env_int('GEMINI_SUPPORT_MAX_OUTPUT_TOKENS', default=420)
GEMINI_SUPPORT_TEMPERATURE = env_float('GEMINI_SUPPORT_TEMPERATURE', default=0.35)
GEMINI_INTERACTIONS_URL = os.environ.get('GEMINI_INTERACTIONS_URL', 'https://generativelanguage.googleapis.com/v1beta/interactions')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_SUPPORT_MODEL = os.environ.get('OPENAI_SUPPORT_MODEL', 'gpt-4.1-mini')
OPENAI_SUPPORT_TIMEOUT = env_int('OPENAI_SUPPORT_TIMEOUT', default=12)
OPENAI_SUPPORT_MAX_OUTPUT_TOKENS = env_int('OPENAI_SUPPORT_MAX_OUTPUT_TOKENS', default=420)
OPENAI_RESPONSES_URL = os.environ.get('OPENAI_RESPONSES_URL', 'https://api.openai.com/v1/responses')


# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'
