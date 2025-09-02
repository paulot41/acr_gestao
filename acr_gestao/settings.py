from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-prod")
DEBUG = os.getenv("DEBUG", "0") in {"1", "true", "True"}
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h.strip()]

# Construir CSRF_TRUSTED_ORIGINS a partir dos hosts
CSRF_TRUSTED_ORIGINS = []
for host in ALLOWED_HOSTS:
    host = host.lower()
    if host and host != "localhost" and host != "127.0.0.1":
        scheme = "https" if not DEBUG else "http"
        CSRF_TRUSTED_ORIGINS.append(f"{scheme}://{host}")

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "acr_gestao.multitenant.OrganizationMiddleware",
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
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
