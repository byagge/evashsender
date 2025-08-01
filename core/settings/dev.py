from .base import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
SECRET_KEY = 'django-insecure-change-this-in-production'
DEBUG = False

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'vashsender.ru', 'www.vashsender.ru']

# Надёжные источники для CSRF-проверки
CSRF_TRUSTED_ORIGINS = [
    'https://vashsender.ru',
    'https://www.vashsender.ru',
]

# Безопасные куки (рекомендуется при HTTPS)
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

try:
    from .local import *
except ImportError:
    pass

