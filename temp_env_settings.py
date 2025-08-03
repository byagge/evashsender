# Временные настройки SMTP для тестирования
# Скопируйте эти настройки в файл .env

# Gmail SMTP настройки (для тестирования)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@vashsender.ru

# Или Yandex SMTP настройки
# EMAIL_HOST=smtp.yandex.ru
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_USE_SSL=False
# EMAIL_HOST_USER=your-email@yandex.ru
# EMAIL_HOST_PASSWORD=your-password
# DEFAULT_FROM_EMAIL=noreply@vashsender.ru

# Или локальный SMTP сервер (если установлен)
# EMAIL_HOST=localhost
# EMAIL_PORT=25
# EMAIL_USE_TLS=False
# EMAIL_USE_SSL=False
# EMAIL_HOST_USER=
# EMAIL_HOST_PASSWORD=
# DEFAULT_FROM_EMAIL=noreply@vashsender.ru

print("Скопируйте эти настройки в файл .env")
print("Замените your-email@gmail.com и your-app-password на ваши реальные данные") 