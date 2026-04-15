import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file
load_dotenv(BASE_DIR.parent / ".env")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY
DEBUG = os.getenv("DEBUG", "False") == "True"

if not DEBUG:
    # We import inside the 'if' so it doesn't fail in dev
    # where whitenoise might not be installed.
    from whitenoise.storage import CompressedManifestStaticFilesStorage  # noqa: F401 # type: ignore

    class CustomWhiteNoiseStorage(CompressedManifestStaticFilesStorage):
        """
        Custom storage that ignores the tw/ folder during collectstatic
        """

        def post_process(self, paths, dry_run=False, **options):
            filtered_paths = {
                path: details
                for path, details in paths.items()
                if not path.startswith("tw/")
            }
            return super().post_process(filtered_paths, dry_run, **options)


ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://parking.fswd.site",
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "home",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]

# Only add whitenoise in production
if not DEBUG:
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

MIDDLEWARE += [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "parking.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "src" / "templates"],
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

WSGI_APPLICATION = "parking.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "src" / "db" / "db.sqlite3",
        "OPTIONS": {
            "timeout": 20,
            "init_command": (
                "PRAGMA journal_mode=WAL;"
                "PRAGMA synchronous=NORMAL;"
                "PRAGMA busy_timeout=20000;"
            ),
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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

AUTH_USER_MODEL = "accounts.User"

# --- Authentication Settings ---

# 1. LOGIN_URL: Where Django redirects users if they need to log in (e.g., when accessing a @login_required view).
# This must match the URL name defined in accounts/urls.py
LOGIN_URL = "accounts:login"

# 2. LOGIN_REDIRECT_URL: The URL to redirect users to after successful login.
# Assuming you have a main view in your 'parking' app named 'index' or 'home'.
# Use the namespace (parking) and the URL name (e.g., index).
LOGIN_REDIRECT_URL = "home:index"

# 3. LOGOUT_REDIRECT_URL (Optional but recommended): The URL to redirect users to after logging out.
LOGOUT_REDIRECT_URL = "accounts:login"

# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/
LANGUAGE_CODE = "sr-latn"  # ili 'sr' za ćirilicu

USE_L10N = True

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Directories where Django will look for static files
STATICFILES_DIRS = [
    BASE_DIR / "src" / "static",
]


if DEBUG:
    # Development: Use default static files storage
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    # Production: Use custom WhiteNoise storage that skips tw/ folder
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "parking.settings.CustomWhiteNoiseStorage",  # Use custom storage
        },
    }


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
