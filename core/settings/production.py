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
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

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
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='vashsender'),
        'USER': config('DB_USER', default='vashsender'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'CONN_MAX_AGE': 600,
            'CONN_HEALTH_CHECKS': True,
        },
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
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@vashsender.ru')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

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

# Настройки для высокой производительности
CONN_MAX_AGE = 600
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Настройки сессий
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

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