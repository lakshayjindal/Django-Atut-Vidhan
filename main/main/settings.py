from pathlib import Path
import dj_database_url
import os
from dotenv import load_dotenv

load_dotenv()
# === BASE SETUP ===
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-j73yrt8#0*c7m&dqno$_4$6l%90r%bn03_blq02l*0fa9rbkvd")

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    "*",  # allow all during testing
]

# === APPLICATIONS ===
INSTALLED_APPS = [
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # your apps
    'connect.apps.ConnectConfig',
    'user.apps.UserConfig',
    'siteadmin.apps.SiteadminConfig',
    'search.apps.SearchConfig',
    'plans.apps.PlansConfig',
]

# === MIDDLEWARE ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # whitenoise near top
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'main.urls'

# === TEMPLATES ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'user.context_processors.fallback_images',
            ],
        },
    },
]

# === ASGI / WSGI ===
ASGI_APPLICATION = "main.asgi.application"
WSGI_APPLICATION = 'main.wsgi.application'

# === DATABASE ===
os.environ.setdefault("PGDATABASE", "liftoff_dev")
os.environ.setdefault("PGUSER", "username")
os.environ.setdefault("PGPASSWORD", "")
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGPORT", "5432")
db_live = os.environ.get('DB_LIVE', 'False').lower() == 'true'

if False:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('PGDATABASE'),
            'USER': os.environ.get('PGUSER'),
            'PASSWORD': os.environ.get('PGPASSWORD'),
            'HOST': os.environ.get('PGHOST'),
            'PORT': os.environ.get('PGPORT'),
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.parse(
            "postgresql://postgres:mHykRuIEhfmZBXxnCsvWwCppcyWbnFEq@caboose.proxy.rlwy.net:20664/railway"
        )
    }

# === CHANNELS ===
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# === PASSWORD VALIDATION ===
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# === LOCALIZATION ===
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
USE_L10N = False

# === STATIC & MEDIA ===
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "main/static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# === AUTH / USER MODEL ===
AUTH_USER_MODEL = 'user.User'
LOGIN_URL = "auth/"

# === EMAIL (Gmail SMTP) ===
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = "atutvidhanmatrimony@gmail.com"
EMAIL_HOST_PASSWORD = "htynyxqhcfpzapvt"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

BREVO_API_KEY = os.environ.get('BREVO_API_KEY')

# === SECURITY / CSRF ===
CSRF_TRUSTED_ORIGINS = [
    "https://*.railway.app",
    "https://*.up.railway.app",
    "https://*.onrender.com",
    "https://atutvidhan.com",
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# For Railway (usually HTTP behind proxy)
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# === CUSTOM FALLBACKS ===
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DEFAULT_FEMALE_FALLBACK_URL = "https://krtiayhjqgtsruzboour.supabase.co/storage/v1/object/public/media/profile_images/femaledefault.png"
DEFAULT_MALE_FALLBACK_URL = "https://krtiayhjqgtsruzboour.supabase.co/storage/v1/object/public/media/profile_images/maledefault.png"

# === DATE FORMATS ===
DATE_INPUT_FORMATS = ['%d-%m-%Y']
DATE_FORMAT = 'd-m-Y'

# PORT = os.getenv("PORT", "8000")
# print(f"🚀 Django running on port {PORT}")
