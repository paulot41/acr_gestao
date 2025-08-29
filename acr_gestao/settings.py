"""
Django settings for acr_gestao project.
"""

from pathlib import Path
import os

# -------------------------
# Paths & Base
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# Core security & debug (12-factor)
# -------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "0").lower() in ("1", "true", "yes", "on")

# Hosts: lê da env ou usa defaults úteis (IP/localhost + domínios locais)
DEFAULT_HOSTS = ["127.0.0.1", "localhost", "acr.local", "gym.local"]
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", ",".join(DEFAULT_HOSTS)).split(",")
    if h.strip()
]

# CSRF trusted origins: se não definido, derivamos de ALLOWED_HOSTS
def _default_csrf_from_hosts(hosts: list[str]) -> list[str]:
    origins: list[str] = []
    for h in hosts:
        # ignora wildcard e vazios
        if not h or h == "*":
            continue
        origins.append(f"http://{h}")
        origins.append(f"https://{h}")
    # remover duplicados mantendo ordem
    seen = set()
    uniq = []
    for o in origins:
        if o not in seen:
            uniq.append(o)
            seen.add(o)
    return uniq

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv("CSRF_TRUSTED_ORIGINS", ",".join(_default_csrf_from_hosts(ALLOWED_HOSTS))).split(",")
    if o.strip()
]

# Quando atrás de proxy (Caddy), isto ajuda o Django a reconhecer HTTPS
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -------------------------
# Applications
# -------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps de terceiros (se/quando precisares, podes ativar)
    # "rest_framework",
    # "django_filters",
    # Apps do projeto
    "core",
]

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Multitenant por domínio
    "acr_gestao.multitenant.OrganizationMiddleware",
]

ROOT_URLCONF = "acr_gestao.urls"

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

WSGI_APPLICATION = "acr_gestao.wsgi.application"

# -------------------------
# Database (Postgres via env; SQLite por omissão)
# -------------------------
if os.getenv("DB_ENGINE"):
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE"),
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
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

# -------------------------
# Password validation
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -------------------------
# I18N / TZ
# -------------------------
LANGUAGE_CODE = "pt-pt"
TIME_ZONE = "Europe/Lisbon"
USE_I18N = True
USE_TZ = True

# -------------------------
# Static & Media
# -------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------
# Django defaults
# -------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
