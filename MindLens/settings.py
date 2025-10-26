"""
Django settings for MindLens project.
"""

from pathlib import Path
import os  
from dotenv import load_dotenv

# ------------------------------
# BASE CONFIGURATION
# ------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-3gp)3x@ss^$7ohhkeca*!6os@vr5%c#x3hude^@ypsy2edyv(d"
DEBUG = True
ALLOWED_HOSTS = []

# ------------------------------
# APPLICATIONS
# ------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    'django.contrib.humanize'
    
]

# ------------------------------
# MIDDLEWARE
# ------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "users.middleware.SessionTrackingMiddleware",
]

ROOT_URLCONF = "MindLens.urls"

# ------------------------------
# TEMPLATES
# ------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],  
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

WSGI_APPLICATION = "MindLens.wsgi.application"

# ------------------------------
# DATABASE
# ------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "mindlens_db",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5433",
        "OPTIONS": {
            "client_encoding": "UTF8",
        },
    }
}
#
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# ------------------------------
# PASSWORD VALIDATION
# ------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------
# INTERNATIONALIZATION
# ------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ------------------------------
# STATIC & MEDIA FILES
# ------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]  
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")   

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------
# CUSTOM USER MODEL
# ------------------------------
AUTH_USER_MODEL = "users.User"

# ------------------------------
# DEFAULT AUTO FIELD
# ------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
# ------------------------------
#dotenv
# ------------------------------
load_dotenv()
# Access the environment variables
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
DEBUG=True
# settings.py

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"          # Serveur SMTP
EMAIL_PORT = 587                        # Port TLS
EMAIL_USE_TLS = True                     # Sécurisé
EMAIL_HOST_USER = "tesnimsatouri@gmail.com"  # L’email de la plateforme
EMAIL_HOST_PASSWORD = "remv cetq iyqc kkrs" # Mot de passe d’application Gmail
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER