# Local settings for production
# This file should contain sensitive settings like email credentials

# Email settings for production
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Для продакшена
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Для тестирования
EMAIL_HOST = 'localhost'  # Change this to your SMTP server
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ''  # Add your SMTP username if needed
EMAIL_HOST_PASSWORD = ''  # Add your SMTP password if needed
DEFAULT_FROM_EMAIL = 'noreply@vashsender.ru'
SERVER_EMAIL = DEFAULT_FROM_EMAIL