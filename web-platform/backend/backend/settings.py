from pathlib import Path
import os
from datetime import timedelta
import environ


BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    USE_CLOUD_STORAGE=(bool, False)
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

DEBUG = env.bool('DEBUG', default=False) 
SECRET_KEY = env('SECRET_KEY')
USE_CLOUD = env.bool('USE_CLOUD_STORAGE', default=False)

BASE_URL = env("BASE_URL")
BASE_FRONT_URL = env("BASE_FRONT_URL")

def extract_hostname(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.hostname if parsed.hostname else url

ALLOWED_HOSTS = [
    extract_hostname(BASE_URL),
    extract_hostname(BASE_FRONT_URL),
    'localhost',
    '127.0.0.1',
    'host.docker.internal'
    
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',
    'django.contrib.staticfiles',

    'rest_framework',
    'channels',
    'django_celery_results',
    'django_celery_progress',
    'celery',
    'corsheaders',
    'storages',
    'resumable',
    'network.apps.RolesAccessTypesConfig',
    
    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('localhost', 6379)],
        },
    },
}

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'
ASGI_APPLICATION = 'backend.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
    
        # 'OPTIONS': {
        #     'target_session_attrs': 'read-write',
        #     'sslmode': 'verify-full',
        # },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/' 
MEDIA_ROOT = '/app/backend/media'


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.DjangoModelPermissions",),
}


LOGIN_URL = "/api/v1/signin"

SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('Bearer',),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=2),
    'USER_ID_FIELD': 'user_id', 
    'USER_ID_CLAIM': 'user_id',  
}
 
CORS_ALLOWED_ORIGINS = [BASE_FRONT_URL]
CSRF_TRUSTED_ORIGINS = [BASE_FRONT_URL]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-requested-with',
    'X-CSRFToken',
    'Authorization',
]

CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


AUTH_USER_MODEL = 'network.Users'

CELERY_BROKER_URL = env('CELERY_BROKER_URL')  
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'


if USE_CLOUD:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                'endpoint_url': env('URL_STORAGE'),
                'access_key': env('ACCESS_KEY_ID'),
                'secret_key': env('SECRET_ACCESS_KEY') ,
                'bucket_name': env('BUCKET_NAME'),
                'region_name': 'ru-central1',
                'signature_version': 's3v4',
                'file_overwrite': True,
                'default_acl': None,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                'endpoint_url': env('URL_STORAGE'),
                'access_key': env('ACCESS_KEY_ID'),
                'secret_key': env('SECRET_ACCESS_KEY') ,
                'region_name': 'ru-central1',
                'signature_version': 's3v4',
                'default_acl': None,
            },
        },
    }
else:
    STORAGES = {
            "default": {
                "BACKEND": "network.storage.OverwriteStorage",
                "OPTIONS": {
                    "location": MEDIA_ROOT,
                },
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }
    DEFAULT_FILE_STORAGE = STORAGES['default']['BACKEND']


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler',},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'network': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


DATA_UPLOAD_MAX_MEMORY_SIZE = 1073741824


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"




