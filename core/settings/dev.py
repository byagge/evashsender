from .base import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
SECRET_KEY = 'django-insecure-change-this-in-production'
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'vashsender.ru', 'www.vashsender.ru']

try:
    from .local import *
except ImportError:
    pass