from .base import *
import os
from decouple import config

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here')

ALLOWED_HOSTS = [
    'vashsender.ru',
    'www.vashsender.ru',
    'api.vashsender.ru',
    'admin.vashsender.ru',
    'localhost',
    '127.0.0.1',
    '146.185.196.123',
]

# Надёжные источники для CSRF-проверки
CSRF_TRUSTED_ORIGINS = [
    'https://vashsender.ru',
    'https://www.vashsender.ru',
    'https://api.vashsender.ru',
    'https://admin.vashsender.ru',
]

# Безопасные куки (обязательно при HTTPS)
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # Должно быть False для доступа через JavaScript
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Настройки безопасности
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Используем SQLite для простоты
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Redis для кэширования и Celery
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# Кэширование
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'vashsender',
        'TIMEOUT': 300,
    }
}

# Celery Configuration для продакшена
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Moscow'

# Оптимизация Celery для высокой нагрузки
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_ALWAYS_EAGER = False

# Email settings для продакшена
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=25, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@vashsender.ru')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Дополнительные настройки SMTP для обхода проблем с SSL
EMAIL_USE_LOCALTIME = True
EMAIL_TIMEOUT = 30

# Настройки для отладки SMTP (отключить в продакшене)
import ssl
EMAIL_SSL_CONTEXT = ssl.create_default_context()
EMAIL_SSL_CONTEXT.check_hostname = False
EMAIL_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# Email sending configuration для продакшена
EMAIL_BATCH_SIZE = config('EMAIL_BATCH_SIZE', default=200, cast=int)
EMAIL_RATE_LIMIT = config('EMAIL_RATE_LIMIT', default=100, cast=int)
EMAIL_MAX_RETRIES = config('EMAIL_MAX_RETRIES', default=3, cast=int)
EMAIL_RETRY_DELAY = config('EMAIL_RETRY_DELAY', default=60, cast=int)
EMAIL_CONNECTION_TIMEOUT = config('EMAIL_CONNECTION_TIMEOUT', default=30, cast=int)
EMAIL_SEND_TIMEOUT = config('EMAIL_SEND_TIMEOUT', default=60, cast=int)

# Статические файлы
STATIC_ROOT = '/var/www/vashsender/static/'
MEDIA_ROOT = '/var/www/vashsender/media/'
STATICFILES_DIRS = []

# Настройки для высокой производительности
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB для больших файлов импорта
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000  # Увеличиваем лимит полей
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100MB для файлов
FILE_UPLOAD_TEMP_DIR = '/tmp'

# Database connection settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        'CONN_MAX_AGE': 600,
    }
}

# Настройки сессий - ИСПРАВЛЕНО
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Используем базу данных
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Authentication settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Настройки для отправки больших объемов писем
EMAIL_BACKEND_TIMEOUT = 30
EMAIL_BACKEND_RETRY_TIMEOUT = 60

# Мониторинг и метрики
ENABLE_METRICS = True
METRICS_INTERVAL = 60  # секунды

# Настройки безопасности для email
EMAIL_USE_VERIFICATION = True
EMAIL_VERIFICATION_TIMEOUT = 3600  # 1 час

# Настройки для автоматического масштабирования
AUTO_SCALE_WORKERS = True
MAX_WORKERS = 32
MIN_WORKERS = 4
WORKER_SCALE_THRESHOLD = 1000  # писем в очереди

# Настройки для мониторинга здоровья системы
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_INTERVAL = 300  # 5 минут

# Настройки для бэкапов
BACKUP_ENABLED = True
BACKUP_INTERVAL = 86400  # 24 часа
BACKUP_RETENTION_DAYS = 30

# Логирование для продакшена
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/vashsender/django.log',
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'celery_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/vashsender/celery.log',
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'celery': {
            'handlers': ['celery_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.campaigns': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Настройки для безопасности
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True

# Настройки для статических файлов
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Настройки для медиа файлов
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Настройки для сессий
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Настройки для кэширования
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'vashsender'

# Настройки для безопасности
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Настройки для email
EMAIL_SUBJECT_PREFIX = '[VashSender] '
EMAIL_USE_LOCALTIME = True

# Настройки для Celery
CELERY_TASK_ROUTES = {
    'apps.campaigns.tasks.send_campaign': {'queue': 'campaigns'},
    'apps.campaigns.tasks.send_email_batch': {'queue': 'email'},
    'apps.campaigns.tasks.send_single_email': {'queue': 'email'},
    'apps.campaigns.tasks.test_celery': {'queue': 'campaigns'},
}

CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_QUEUES = {
    'default': {'exchange': 'default', 'routing_key': 'default'},
    'email': {'exchange': 'email', 'routing_key': 'email', 'queue_arguments': {'x-max-priority': 10}},
    'campaigns': {'exchange': 'campaigns', 'routing_key': 'campaigns', 'queue_arguments': {'x-max-priority': 10}},
}

# Настройки для мониторинга
FLOWER_PORT = 5555
FLOWER_HOST = '0.0.0.0'

# Настройки для производительности
# TEMPLATES[0]['OPTIONS']['debug'] = False  # УДАЛИТЬ ЭТУ СТРОКУ
# TEMPLATES[0]['OPTIONS']['auto_reload'] = False  # УДАЛИТЬ ЭТУ СТРОКУ

# Настройки для безопасности
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Настройки для email
EMAIL_TIMEOUT = 30

# Настройки для Celery
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_ALWAYS_EAGER = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_RESULT_EXPIRES = 3600

# Переопределяем TEMPLATES для продакшена
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
            os.path.join(BASE_DIR, "templates"),
        ],
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