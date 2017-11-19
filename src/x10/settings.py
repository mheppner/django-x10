"""Main project settings."""
from __future__ import absolute_import

import environ

try:
    import debug_toolbar
except ImportError:
    debug_toolbar = None

try:
    import asgi_ipc
except ImportError:
    asgi_ipc = None


# inner project dir (manage.py)
base_dir = environ.Path(__file__) - 1
BASE_DIR = base_dir()

# root project dir (git root)
root_dir = base_dir - 2
ROOT_DIR = root_dir()

# data storage
data_dir = root_dir.path('data')
DATA_DIR = data_dir()

# load default environment from file
env = environ.Env(DEBUG=(bool, False),)
environ.Env.read_env(root_dir.path('.env')())


'''
Base settings
'''
DEBUG = env('DEBUG')
SECRET_KEY = env('SECRET_KEY')
INTERNAL_IPS = env.list('INTERNAL_IPS', default=[])
HTTPS_ONLY = env.bool('HTTPS_ONLY', default=False)
WSGI_APPLICATION = 'x10.wsgi.application'
ROOT_URLCONF = 'x10.urls'


'''
Models
'''
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'cachalot',
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.storage',
    'channels',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'adminsortable2',
    'crispy_forms',
    'guardian',
    'django_celery_beat',
    'django_celery_results',
    'django_filters',

    'core',
]


'''
Database and cache
'''
DATABASES = {
    'default': env.db(
        default='sqlite:///{}'.format(data_dir('run', 'db.sqlite3'))
    )
}

CACHES = {
    'default': env.cache_url(default='locmemcache://'),
    'file': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': data_dir.path('cache')(),
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    },
}
CACHALOT_ENABLED = env.bool('CACHALOT_ENABLED', default=not DEBUG)


'''
Sites framework
'''
SITE_ID = env.int('SITE_ID', default=1)


'''Channels'''
CHANNEL_LAYERS = {
    'default': {
        'ROUTING': 'x10.routing.routes',
    },
}

if asgi_ipc is not None:
    CHANNEL_LAYERS['default']['BACKEND'] = 'asgi_ipc.IPCChannelLayer'
else:
    # in-memory layer does not work across processes
    CHANNEL_LAYERS['default']['BACKEND'] = 'asgiref.inmemory.ChannelLayer'


'''
Authentication
'''
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
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)


'''
Email
'''
EMAIL_BACKEND = env.str('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')


'''
Media
'''
MEDIA_ROOT = env.path('MEDIA_ROOT', default=data_dir.path('media')(), required=True)()
MEDIA_URL = env.str('MEDIA_URL', default='/media/')


'''
Static files
'''
STATIC_ROOT = env.path('STATIC_ROOT', default=data_dir.path('static')(), required=True)()
STATIC_URL = env.str('STATIC_URL', default='/static/')


'''
Templates and UI
'''
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
if not DEBUG:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]
    TEMPLATES[0]['APP_DIRS'] = False


'''
Globalization
'''
USE_I18N = False
USE_L10N = True
USE_TZ = True
TIME_ZONE = env.str('TIME_ZONE', default='America/New_York')


'''
HTTP
'''
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


'''
Security
'''
CSRF_COOKIE_DOMAIN = env.str('CSRF_COOKIE_DOMAIN', default=None)
CSRF_COOKIE_NAME = env.str('CSRF_COOKIE_NAME', default='csrftoken')
CSRF_COOKIE_SECURE = HTTPS_ONLY


'''
Session
'''
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_DOMAIN = env.str('SESSION_COOKIE_DOMAIN', default=None)
SESSION_COOKIE_NAME = env.str('SESSION_COOKIE_NAME', default='session')
SESSION_COOKIE_SECURE = HTTPS_ONLY


'''
Debug
'''
if debug_toolbar is not None:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')


'''
REST Framework
'''
REST_FRAMEWORK = {
    'DEFAULT_MODEL_SERIALIZER_CLASS': 'rest_framework.serializers.HyperlinkedModelSerializer',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '2/second',
        'user': '15/second'
    },
}


'''
Celery
'''
CELERY_BROKER_URL = env.str('CELERY_BROKER_URL', default='amqp://')
CELERY_RESULT_BACKEND = env.str('CELERY_RESULT_BACKEND', default='django-cache')
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'
CELERY_TIMEZONE = TIME_ZONE


'''
App settings
'''
X10_SERIAL = env.str('X10_SERIAL', default='/dev/cu.usbserial')
X10_LATITUDE = env.float('X10_LATITUDE', default=38.889857)
X10_LONGITUDE = env.float('X10_LONGITUDE', default=-77.009954)


'''
Logging
'''
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': ('%(levelname)s %(asctime)s %(module)s %(process)d '
                       '%(thread)d %(message)s')
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'core.management.commands': {
            'handlers': ['console'],
            'propagate': True
        },
    }
}
