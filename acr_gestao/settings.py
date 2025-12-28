from pathlib import Path
from django.urls import reverse_lazy
import os
import secrets

BASE_DIR = Path(__file__).resolve().parent.parent

# Gerar SECRET_KEY segura se não estiver definida
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(50)
    print("WARNING: Using generated SECRET_KEY. Set SECRET_KEY environment variable for production.")

DEBUG = os.getenv("DEBUG", "0") in {"1", "true", "True"}
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

# Adicionar localhost para health checks em produção
if not DEBUG and "localhost" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("localhost")

# Construir CSRF_TRUSTED_ORIGINS a partir dos hosts
CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    host = host.lower()
    if host and host != "localhost" and host != "127.0.0.1":
        scheme = "https" if not DEBUG else "http"
        CSRF_TRUSTED_ORIGINS.append(f"{scheme}://{host}")

# Adicionar explicitamente localhost:8080 para desenvolvimento Docker
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost",
        "http://127.0.0.1"
    ])

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Configurações de segurança HTTPS (controladas por variáveis de ambiente)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "1") in {"1", "true", "True"} and not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000")) if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "1") in {"1", "true", "True"} and not DEBUG
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "1") in {"1", "true", "True"} and not DEBUG
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1") in {"1", "true", "True"} and not DEBUG
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "1") in {"1", "true", "True"} and not DEBUG
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")
SECURE_CROSS_ORIGIN_OPENER_POLICY = os.getenv("SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin")
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = os.getenv("SECURE_CROSS_ORIGIN_RESOURCE_POLICY", "same-site")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "reports",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.middleware.RequestIdMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    'core.middleware.OrganizationMiddleware',
    'core.auth_views.UserRoleMiddleware',  # Middleware personalizado para papéis de utilizador
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "acr_gestao.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "acr_gestao.wsgi.application"
ASGI_APPLICATION = "acr_gestao.asgi.application"

# DB: Postgres via env; fallback sqlite em dev
DB_ENGINE = os.getenv("DB_ENGINE", "")
if DB_ENGINE:
    DATABASES = {"default": {
        "ENGINE": DB_ENGINE,
        "NAME": os.getenv("DB_NAME", "acrdb"),
        "USER": os.getenv("DB_USER", "acruser"),
        "PASSWORD": os.getenv("DB_PASSWORD", "acrpass"),
        "HOST": os.getenv("DB_HOST", "db"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

LANGUAGE_CODE = "pt-pt"
LANGUAGES = [
    ("pt-pt", "Portuguese (Portugal)"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# WhiteNoise: serve static files directly from Django in production
if not DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email (SMTP) configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "0") in {"1", "true", "True"}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

# Configurações de segurança para produção
if not DEBUG:
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# Observabilidade (Sentry) - opcional por ambiente
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            send_default_pii=False,
        )
    except ImportError as exc:
        raise RuntimeError("SENTRY_DSN definido, mas sentry-sdk não está instalado") from exc

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "core.logging_utils.RequestIdFilter"},
    },
    "formatters": {
        "json": {"()": "core.logging_utils.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", LOG_LEVEL),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_REQUEST_LOG_LEVEL", LOG_LEVEL),
            "propagate": False,
        },
    },
}

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append('rest_framework.renderers.BrowsableAPIRenderer')

# URLs de autenticação
LOGIN_URL = reverse_lazy('core:login')
LOGIN_REDIRECT_URL = reverse_lazy('core:home')
