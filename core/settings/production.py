from .base import *

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = True

ALLOWED_HOSTS = [
    'vashsender.ru',
    'www.vashsender.ru',
    '127.0.0.1',        # на всякий локальный доступ
    'localhost',
    '146.185.196.123',
]

# Надёжные источники для CSRF-проверки
CSRF_TRUSTED_ORIGINS = [
    'https://vashsender.ru',
    'https://www.vashsender.ru',
]

# Чтобы CSRF не рвалась из‑за отсутствия Origin/Referer
CSRF_TRUST_ALL_ORIGINS = True

# 3. Поскольку вы сидите за Nginx с TLS, сообщите Django, что прокси передаёт HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Безопасные куки (рекомендуется при HTTPS)
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# Чтобы браузер отправлял куки при всех запросах (даже POST с fetch)
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SAMESITE = 'None'

try:
    from .local import *
except ImportError:
    pass