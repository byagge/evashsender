from .base import *
from decouple import config
import os

# SECURITY WARNING: don't run with debug turned on in production!
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

try:
    from .local import *
except ImportError:
    pass
