"""
eSYNAPSE 360 — Configuración del proyecto Django (Fase 0).
Metrindust S.A.C. — Sistema Integrado de Gestión Empresarial.
"""

from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# En producción: mover a variable de entorno (ej: os.environ['SECRET_KEY'])
SECRET_KEY = 'django-insecure-8wxz^&kybj@tq)qwom#ona*et=f1w!*o(3gttcdsip29l!8s5v'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Terceros
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    # Apps del SIGE
    'core',
    'esynapse_sig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # debe ir antes de CommonMiddleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Auditoría automática del SIGE (regla #4 del CLAUDE.md)
    'core.middleware.AuditoriaMiddleware',
]

ROOT_URLCONF = 'esynapse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'esynapse.wsgi.application'


# Database — SQLite en desarrollo, PostgreSQL en producción
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Modelo de usuario personalizado (Capa 0 — CLAUDE.md)
AUTH_USER_MODEL = 'core.Usuario'


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}


# SimpleJWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,  # invalida sesiones al desactivar usuario
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


# CORS — frontend React en desarrollo
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',  # Vite
    'http://localhost:3000',  # CRA / Next
    'http://127.0.0.1:5173',
    'http://127.0.0.1:3000',
]


# Internationalization — Perú
LANGUAGE_CODE = 'es-pe'

TIME_ZONE = 'America/Lima'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Archivos subidos (documentos, evidencias)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Permitir que el visor integrado muestre PDFs propios en iframes del mismo origen
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
