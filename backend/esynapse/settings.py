"""
eSYNAPSE 360 — Configuración del proyecto Django (Fase 0).
Metrindust S.A.C. — Sistema Integrado de Gestión Empresarial.
"""

import os
from datetime import timedelta
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Modo pruebas: el lanzador de pruebas fija ESYNAPSE_MODO=pruebas y el sistema
# trabaja sobre una copia de la base y de los archivos subidos, sin tocar los reales.
MODO_PRUEBAS = os.environ.get('ESYNAPSE_MODO', '').strip().lower() == 'pruebas'


def _secreto_local():
    """Clave secreta fuera del código: variable de entorno ESYNAPSE_SECRET_KEY o archivo local backend/.env
    (SECRET_KEY=...), que se crea solo la primera vez. El .env no va a Git ni a la carpeta limpia."""
    clave = os.environ.get('ESYNAPSE_SECRET_KEY', '').strip()
    if clave:
        return clave
    archivo = BASE_DIR / '.env'
    if archivo.exists():
        for linea in archivo.read_text(encoding='utf-8').splitlines():
            if linea.strip().startswith('SECRET_KEY='):
                valor = linea.split('=', 1)[1].strip()
                if valor:
                    return valor
    import secrets
    clave = secrets.token_urlsafe(50)
    with open(archivo, 'a', encoding='utf-8') as f:
        f.write(f'SECRET_KEY={clave}\n')
    return clave


SECRET_KEY = _secreto_local()

# Los certificados internos de firma ya emitidos se cifraron con una contraseña derivada de la clave anterior; se
# conserva esa base solo para abrirlos (los archivos .p12 son locales). Al pasar a certificados reales (fase 3) se
# reemplaza.
CLAVE_CERTIFICADOS_BASE = os.environ.get('ESYNAPSE_CLAVE_CERTIFICADOS',
                                         'django-insecure-8wxz^&kybj@tq)qwom#ona*et=f1w!*o(3gttcdsip29l!8s5v')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Solo detrás de un proxy inverso propio (producción) se confía en X-Forwarded-For para la IP del log y las firmas.
PROXY_CONFIABLE = os.environ.get('ESYNAPSE_PROXY_CONFIABLE', '') == '1'


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
    'quejas',
    'procesos',
    'cambios',
    'riesgos',
    'legal',
    'sst',
    'organizacion',
    'capacitacion',
    'ambiente',
    'revision',
    'tnc',
    'cumplimiento',
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
        'NAME': BASE_DIR / ('db_pruebas.sqlite3' if MODO_PRUEBAS else 'db.sqlite3'),
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
    'DEFAULT_PAGINATION_CLASS': 'core.paginacion.PaginacionSIG',
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
MEDIA_ROOT = BASE_DIR / ('media_pruebas' if MODO_PRUEBAS else 'media')

# Permitir que el visor integrado muestre PDFs propios en iframes del mismo origen
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
