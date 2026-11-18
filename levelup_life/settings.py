"""
Django settings for LevelUp Life.

Secrets and database credentials are read from a local ".env" file
(see ".env.example"). The project requires PostgreSQL / Supabase.
"""
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# --- Core ---------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is not set. Copy .env.example to .env and fill it in."
    )

DEBUG = env_bool("DJANGO_DEBUG", False)

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

# --- Apps ---------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",  # failed-login lockout (BR-03)
    "accounts",
    "gamification",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.UserTimezoneMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",  # must be last
]

ROOT_URLCONF = "levelup_life.urls"

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

WSGI_APPLICATION = "levelup_life.wsgi.application"

# --- Database (PostgreSQL / Supabase only) -------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL is not set. Add your PostgreSQL or Supabase connection "
        "string to .env (see .env.example)."
    )
if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
    raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL / Supabase URL. SQLite is not allowed.")

DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}

# --- Auth ---------------------------------------------------------------
# Custom user model with email as the login field (SDD 4.1). Supabase Auth is NOT used.
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # enforces the lockout; must be first
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("email", "display_name")}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},                                   # BR-02: at least 8 characters
    {"NAME": "accounts.validators.LetterAndNumberValidator"},         # BR-02: a letter and a number
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# BR-03: lock an account for 15 minutes after 5 consecutive failed logins.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["username"]          # lock the account (email), not the IP address
AXES_USERNAME_FORM_FIELD = "username"           # Django passes the login to backends as "username"
AXES_USERNAME_CALLABLE = "accounts.utils.axes_username"
AXES_RESET_ON_SUCCESS = True                    # only *consecutive* failures count
AXES_LOCKOUT_TEMPLATE = "registration/locked.html"
# BR-03 locks the *account*, so we deliberately lock by email only. The trade-off (someone can deliberately
# trigger a 15-minute lock on another person's account) is documented in the README.
SILENCED_SYSTEM_CHECKS = ["axes.W006"]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

# --- i18n ---------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"  # each user has their own time_zone (activated by middleware)
USE_I18N = True
USE_TZ = True

# --- Static -----------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Map Django message levels to the CSS class names used in the templates.
MESSAGE_TAGS = {message_constants.ERROR: "error"}
