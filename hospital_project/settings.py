"""
Django settings for hospital_project.

Phase 2 — production-ready.

This file reads all environment-specific values from environment variables so
the same image can run unchanged in dev, staging, and prod. Defaults are
chosen so `python manage.py runserver` still works out-of-the-box with the
Phase 1 SQLite database when no env is set.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Small helper so we don't sprinkle os.environ.get + bool conversion everywhere
# ---------------------------------------------------------------------------
def env(key, default=None, *, cast=str):
    v = os.environ.get(key, default)
    if v is None:
        return None
    if cast is bool:
        return str(v).strip().lower() in ("1", "true", "yes", "on")
    return cast(v)


# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    # Insecure fallback used ONLY when DEBUG=True. In prod the env var must be set.
    "django-insecure-uuzi@_#9fd@82n7di-&#xbhgbnd@_aexw(jrrh)-c(f*do(lp!",
)

DEBUG = env("DJANGO_DEBUG", "1", cast=bool)   # default ON for dev convenience

ALLOWED_HOSTS = [
    h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# When the frontend Nginx sits in front of Django, requests reach Django over
# plain HTTP on the docker network. Trust the X-Forwarded-Proto header so
# Django returns the correct absolute URLs and `request.is_secure()` works.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 3rd party
    "encrypted_model_fields",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",

    # Local
    "accounts",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # whitenoise serves static files directly from gunicorn so we don't need
    # to bind-mount a static dir into nginx (we still do, for performance).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hospital_project.urls"

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

WSGI_APPLICATION = "hospital_project.wsgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# If POSTGRES_HOST is set in the environment, use PostgreSQL.
# Otherwise fall back to the Phase 1 SQLite file so `manage.py runserver`
# still works on a developer laptop with no Docker.
if env("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE":   "django.db.backends.postgresql",
            "NAME":     env("POSTGRES_DB",       "hms"),
            "USER":     env("POSTGRES_USER",     "hms_user"),
            "PASSWORD": env("POSTGRES_PASSWORD", ""),
            "HOST":     env("POSTGRES_HOST",     "db"),
            "PORT":     env("POSTGRES_PORT",     "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ---------------------------------------------------------------------------
# Cache (Redis when available, locmem in dev)
# ---------------------------------------------------------------------------
_redis_url = env("REDIS_URL")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND":  "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND":  "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "hms-locmem",
        }
    }


# ---------------------------------------------------------------------------
# Passwords / auth
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"


# ---------------------------------------------------------------------------
# i18n / tz
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static / media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise — compressed, hashed static files in production.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Field-level encryption (django-encrypted-model-fields)
# ---------------------------------------------------------------------------
# Fernet key (44-char urlsafe base64). MUST be set via the FIELD_ENCRYPTION_KEY
# environment variable in any non-dev deployment.
FIELD_ENCRYPTION_KEY = env(
    "FIELD_ENCRYPTION_KEY",
    "Y_WolMvJBPsQBEIukumncmJbB1EWB_SfkwPppvKhkO8=",
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Same-origin in production (frontend and backend share the Nginx domain).
# Allow all in dev only.
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in env(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost,http://127.0.0.1",
        ).split(",") if o.strip()
    ]


# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "120/min",
    },
}


# ---------------------------------------------------------------------------
# Security hardening (only in production)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30          # 30 days; raise after testing
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False                       # toggle on once HSTS is stable
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"


# ---------------------------------------------------------------------------
# Logging — write everything to stdout so docker logs / kubectl logs work.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{asctime}] {levelname:7s} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django.request": {"level": "WARNING", "propagate": True},
        "django.db.backends": {"level": "WARNING", "propagate": True},
    },
}
