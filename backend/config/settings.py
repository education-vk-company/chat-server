import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None, cast=str):
    value = os.environ.get(key, default)
    if value is None:
        return None
    if cast is bool:
        return str(value).lower() in ("1", "true", "yes", "on")
    return cast(value)


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key")
DEBUG = env("DJANGO_DEBUG", "0", cast=bool)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.users",
    "apps.chats",
    "apps.messaging",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "messenger"),
        "USER": env("POSTGRES_USER", "messenger"),
        "PASSWORD": env("POSTGRES_PASSWORD", "messenger"),
        "HOST": env("POSTGRES_HOST", "postgres"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = env("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", "redis://redis:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

JWT_SECRET_KEY = env("JWT_SECRET_KEY", "insecure-dev-jwt-secret")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TTL_SECONDS = env("JWT_ACCESS_TTL_SECONDS", "900", cast=int)
JWT_REFRESH_TTL_SECONDS = env("JWT_REFRESH_TTL_SECONDS", "2592000", cast=int)

CENTRIFUGO_API_URL = env("CENTRIFUGO_API_URL", "http://centrifugo:8000/api")
CENTRIFUGO_HTTP_API_KEY = env("CENTRIFUGO_HTTP_API_KEY", "insecure-dev-api-key")
CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY = env(
    "CENTRIFUGO_CLIENT_TOKEN_HMAC_SECRET_KEY", "insecure-dev-centrifugo-secret"
)
CENTRIFUGO_TOKEN_TTL_SECONDS = env("CENTRIFUGO_TOKEN_TTL_SECONDS", "300", cast=int)

MAX_UPLOAD_SIZE_BYTES = env("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024), cast=int)

CORS_ALLOWED_ORIGINS = [o.strip() for o in env("CORS_ALLOWED_ORIGINS", "*").split(",") if o.strip()]
