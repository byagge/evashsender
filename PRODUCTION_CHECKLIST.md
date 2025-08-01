# 🚀 Чек-лист для развертывания VashSender на продакшене

## 📋 Предварительная подготовка

### ✅ Системные требования
- [ ] Ubuntu 20.04+ или CentOS 8+
- [ ] Python 3.8+
- [ ] PostgreSQL 12+
- [ ] Redis 6+
- [ ] Nginx
- [ ] Минимум 4GB RAM
- [ ] Минимум 20GB свободного места

### ✅ Домены и SSL
- [ ] Домен настроен и указывает на сервер
- [ ] SSL сертификат получен (Let's Encrypt)
- [ ] DNS записи настроены (A, CNAME)
- [ ] SPF, DKIM, DMARC записи настроены

### ✅ SMTP настройки
- [ ] Выделенный IP для отправки писем
- [ ] SMTP сервер настроен (Postfix/SendGrid/Mailgun)
- [ ] Репутация IP проверена
- [ ] Rate limits настроены

## 🔧 Установка и настройка

### ✅ Базовая установка
```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка зависимостей
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib redis-server nginx git -y

# 3. Создание пользователя
sudo useradd -m -s /bin/bash vashsender
sudo usermod -aG sudo vashsender
```

### ✅ База данных
```bash
# 1. Создание базы данных
sudo -u postgres createdb vashsender
sudo -u postgres createuser vashsender
sudo -u postgres psql -c "ALTER USER vashsender WITH PASSWORD 'your-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE vashsender TO vashsender;"
```

### ✅ Redis
```bash
# 1. Настройка Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl status redis-server
```

### ✅ Python окружение
```bash
# 1. Создание виртуального окружения
python3 -m venv /opt/vashsender/venv
source /opt/vashsender/venv/bin/activate

# 2. Установка зависимостей
pip install -r requirements.txt
```

## ⚙️ Конфигурация

### ✅ Переменные окружения
```bash
# 1. Создание .env файла
cp env_production_example.txt .env

# 2. Редактирование .env
nano .env
```

**Обязательные настройки:**
- [ ] SECRET_KEY (сгенерировать новый)
- [ ] DB_PASSWORD
- [ ] EMAIL_HOST_USER
- [ ] EMAIL_HOST_PASSWORD
- [ ] ALLOWED_HOSTS

### ✅ Django настройки
```bash
# 1. Применение миграций
python manage.py migrate

# 2. Создание суперпользователя
python manage.py createsuperuser

# 3. Сбор статических файлов
python manage.py collectstatic --noinput
```

### ✅ Celery настройки
```bash
# 1. Создание директорий для логов
sudo mkdir -p /var/log/vashsender
sudo chown vashsender:vashsender /var/log/vashsender

# 2. Создание systemd сервисов
sudo cp deploy_production.py /opt/vashsender/
cd /opt/vashsender && python deploy_production.py
```

## 🚀 Запуск сервисов

### ✅ Systemd сервисы
```bash
# 1. Запуск сервисов
sudo systemctl start vashsender-celery
sudo systemctl start vashsender-flower
sudo systemctl start vashsender-gunicorn

# 2. Включение автозапуска
sudo systemctl enable vashsender-celery
sudo systemctl enable vashsender-flower
sudo systemctl enable vashsender-gunicorn

# 3. Проверка статуса
sudo systemctl status vashsender-*
```

### ✅ Nginx
```bash
# 1. Активация сайта
sudo ln -s /etc/nginx/sites-available/vashsender /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔍 Проверка и мониторинг

### ✅ Проверка здоровья системы
```bash
# 1. Базовая проверка
python manage.py health_check

# 2. Полная проверка
python manage.py health_check --full
```

### ✅ Мониторинг
- [ ] Flower доступен: http://your-domain.com/flower/
- [ ] Django Admin доступен: http://your-domain.com/admin/
- [ ] API работает: http://your-domain.com/api/
- [ ] Логи проверены: `/var/log/vashsender/`

### ✅ Тестирование отправки
```bash
# 1. Создание тестовой кампании
python manage.py shell
>>> from apps.campaigns.models import Campaign
>>> campaign = Campaign.objects.create(name="Test", subject="Test")
>>> campaign.send()
```

## 🛡️ Безопасность

### ✅ Файрвол
```bash
# 1. Настройка UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### ✅ SSL сертификат
```bash
# 1. Установка Certbot
sudo apt install certbot python3-certbot-nginx

# 2. Получение сертификата
sudo certbot --nginx -d vashsender.ru -d www.vashsender.ru
```

### ✅ Бэкапы
```bash
# 1. Создание скрипта бэкапа
sudo nano /opt/vashsender/backup.sh
chmod +x /opt/vashsender/backup.sh

# 2. Настройка cron
sudo crontab -e
# Добавить: 0 2 * * * /opt/vashsender/backup.sh
```

## 📊 Оптимизация производительности

### ✅ Настройки PostgreSQL
```sql
-- В /etc/postgresql/12/main/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

### ✅ Настройки Redis
```bash
# В /etc/redis/redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### ✅ Настройки Nginx
```nginx
# В /etc/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;
keepalive_timeout 65;
```

## 🚨 Мониторинг и алерты

### ✅ Логирование
- [ ] Логи Django: `/var/log/vashsender/django.log`
- [ ] Логи Celery: `/var/log/vashsender/celery.log`
- [ ] Логи Nginx: `/var/log/nginx/`
- [ ] Логи PostgreSQL: `/var/log/postgresql/`

### ✅ Метрики
- [ ] Количество отправленных писем
- [ ] Время выполнения задач
- [ ] Использование ресурсов
- [ ] Ошибки и исключения

### ✅ Алерты
- [ ] Высокая нагрузка на CPU
- [ ] Нехватка памяти
- [ ] Ошибки отправки писем
- [ ] Недоступность сервисов

## 🔄 Обновления

### ✅ Процедура обновления
```bash
# 1. Бэкап
/opt/vashsender/backup.sh

# 2. Остановка сервисов
sudo systemctl stop vashsender-*

# 3. Обновление кода
git pull origin main

# 4. Обновление зависимостей
pip install -r requirements.txt

# 5. Миграции
python manage.py migrate

# 6. Сбор статических файлов
python manage.py collectstatic --noinput

# 7. Запуск сервисов
sudo systemctl start vashsender-*
```

## 📞 Поддержка

### ✅ Контакты
- [ ] Email для уведомлений настроен
- [ ] Телеграм бот для алертов
- [ ] Документация обновлена
- [ ] Процедуры восстановления готовы

---

## 🎯 Финальная проверка

### ✅ Все системы работают
- [ ] Веб-сайт доступен
- [ ] API отвечает
- [ ] Письма отправляются
- [ ] Мониторинг работает
- [ ] Бэкапы создаются
- [ ] SSL сертификат активен

### ✅ Производительность
- [ ] 10,000 писем отправляются за 15-20 минут
- [ ] Доставляемость 98%+
- [ ] Время отклика API < 200ms
- [ ] Использование ресурсов в норме

**🎉 Система готова к продакшену!** 