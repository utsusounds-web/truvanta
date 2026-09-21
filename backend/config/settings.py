"""
Django settings for Smart Business Operating System (config project).
"""

from pathlib import Path
from datetime import timedelta

from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-.env")
DEBUG = config("DEBUG", default=True, cast=bool)

# Optional dedicated key for encrypting stored credentials at rest
# (see apps/core/crypto.py). If unset, a key is derived from
# SECRET_KEY automatically — this is only worth setting separately if
# you want to be able to rotate SECRET_KEY without also needing to
# re-encrypt every stored credential. Generate one with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = config("FIELD_ENCRYPTION_KEY", default="")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# --- CORS (frontend dev server runs on a different port) ---
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
    cast=Csv(),
)
# Vite picks the next free port (5174, 5175, ...) if 5173 is already in
# use, which silently breaks CORS if only 5173 is allow-listed — the
# browser blocks the response, and the frontend sees a bare network
# error with no useful detail. In dev (DEBUG=True) trust any localhost
# port instead of making that a recurring support question; production
# still only trusts the exact origins above.
if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [r"^http://localhost:\d+$", r"^http://127\.0\.0\.1:\d+$"]
CORS_ALLOW_CREDENTIALS = True

# django-cors-headers only allow-lists a small default set of request
# headers (accept, authorization, content-type, ...). X-Business-ID is
# a custom header the frontend sends on every request except login —
# without it explicitly listed here, the browser's CORS preflight is
# rejected and the request never reaches the server at all. This is
# why login works (no custom header) but every other page fails with
# a generic "can't reach the server" — it's not a connectivity issue,
# it's a blocked preflight. default_headers is the library's own
# built-in list; we extend it rather than replace it.
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = list(default_headers) + ["x-business-id"]

# --- Production security hardening ---
# All default to safe values for local dev (DEBUG=True) and switch on
# automatically once DEBUG=False, without needing separate flags —
# but can still be overridden explicitly via .env if a deployment
# terminates SSL somewhere Django can't see (e.g. behind a load balancer).
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=not DEBUG, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=not DEBUG, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=not DEBUG, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=not DEBUG, cast=bool)
# Prevents browsers guessing content-types (blocks some XSS vectors),
# stops the site being framed by another origin (clickjacking), and
# trims what gets sent in the Referer header to other sites.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    # local apps
    "apps.core",
    "apps.tenants",
    "apps.accounts",
    "apps.audit",
    "apps.products",
    "apps.inventory",
    "apps.sales",
    "apps.customers",
    "apps.suppliers",
    "apps.expenses",
    "apps.shifts",
    "apps.returns",
    "apps.reports",
    "apps.notifications",
    "apps.documents",
    "apps.stock_audit",
    "apps.billing",
    "apps.ledger",
    "apps.quotations",
    "apps.loan_readiness",
    "apps.cashflow",
    "apps.continuity",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# --- Database ---
# Defaults to SQLite for zero-friction local/Windows dev.
# Set DB_ENGINE=postgres in .env for production-grade Postgres.
if config("DB_ENGINE", default="sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="sbos"),
            "USER": config("DB_USER", default="sbos"),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Logos and other uploaded documents. In production point this at S3 /
# a real object store via django-storages — never keep customer/business
# uploads only on a single app server disk.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "login": "10/minute",
        "register": "10/minute",
        "staff_invite": "20/hour",
        "billing": "20/minute",
        "webhook": "120/minute",
    },
}

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# --- Email (Gmail SMTP) — used for notification delivery ---
# Gmail requires an "App Password" (not your normal password) once
# 2-Step Verification is on: https://myaccount.google.com/apppasswords
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

# --- WhatsApp (Meta Cloud API) — used for notification delivery ---
# Create a WhatsApp Business app at https://developers.facebook.com/apps
# to get these two values.
WHATSAPP_ACCESS_TOKEN = config("WHATSAPP_ACCESS_TOKEN", default="")
WHATSAPP_PHONE_NUMBER_ID = config("WHATSAPP_PHONE_NUMBER_ID", default="")

# Truvanta's own Paystack keys, used to bill businesses for paid plans/features
# (separate from each Business's own paystack_secret_key, used for their own
# customer checkout). Falls back to PlatformSettings if set there instead.
PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY", default="")
PAYSTACK_PUBLIC_KEY = config("PAYSTACK_PUBLIC_KEY", default="")
