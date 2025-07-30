from .base import *

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = False

ALLOWED_HOSTS = [
    'vashsender.ru',
    'www.vashsender.ru',
    '127.0.0.1',        # на всякий локальный доступ
    'localhost',
]

try:
    from .local import *
except ImportError:
    pass