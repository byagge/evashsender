#!/usr/bin/env python3
"""
Скрипт для развертывания VashSender на продакшене
"""

import subprocess
import sys
import os
import time
from pathlib import Path


class ProductionDeployer:
    def __init__(self):
        self.project_root = Path.cwd()
        
    def run_command(self, command, description):
        """Выполняет команду с выводом"""
        print(f"🔄 {description}...")
        try:
            result = subprocess.run(command, shell=True, check=True, 
                                  capture_output=True, text=True)
            print(f"✅ {description} завершено успешно")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка при {description.lower()}: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            return False
    
    def check_prerequisites(self):
        """Проверяет необходимые компоненты"""
        print("🔍 Проверка предварительных требований...")
        
        # Проверяем Python
        if not self.run_command("python --version", "Проверка Python"):
            return False
        
        # Проверяем pip
        if not self.run_command("pip --version", "Проверка pip"):
            return False
        
        # Проверяем git
        if not self.run_command("git --version", "Проверка git"):
            return False
        
        return True
    
    def install_dependencies(self):
        """Устанавливает зависимости"""
        print("📦 Установка зависимостей...")
        
        # Обновляем pip
        if not self.run_command("pip install --upgrade pip", "Обновление pip"):
            return False
        
        # Устанавливаем зависимости
        if not self.run_command("pip install -r requirements.txt", "Установка Python зависимостей"):
            return False
        
        return True
    
    def setup_database(self):
        """Настраивает базу данных"""
        print("🗄️ Настройка базы данных...")
        
        # Применяем миграции
        if not self.run_command("python manage.py migrate", "Применение миграций"):
            return False
        
        # Создаем суперпользователя если нужно
        if not self.run_command("python manage.py createsuperuser --noinput", "Создание суперпользователя"):
            print("⚠️ Суперпользователь уже существует или ошибка создания")
        
        return True
    
    def setup_static_files(self):
        """Настраивает статические файлы"""
        print("📁 Настройка статических файлов...")
        
        # Собираем статические файлы
        if not self.run_command("python manage.py collectstatic --noinput", "Сбор статических файлов"):
            return False
        
        return True
    
    def setup_redis(self):
        """Настраивает Redis"""
        print("🔴 Настройка Redis...")
        
        # Проверяем, запущен ли Redis
        try:
            result = subprocess.run("redis-cli ping", shell=True, capture_output=True, text=True)
            if result.stdout.strip() == 'PONG':
                print("✅ Redis уже запущен")
                return True
        except:
            pass
        
        # Пытаемся запустить Redis
        print("🚀 Запуск Redis...")
        if not self.run_command("redis-server --daemonize yes", "Запуск Redis"):
            print("⚠️ Не удалось запустить Redis. Убедитесь, что Redis установлен.")
            return False
        
        return True
    
    def setup_celery(self):
        """Настраивает Celery"""
        print("🌿 Настройка Celery...")
        
        # Проверяем, что Redis доступен
        time.sleep(2)
        try:
            result = subprocess.run("redis-cli ping", shell=True, capture_output=True, text=True)
            if result.stdout.strip() != 'PONG':
                print("❌ Redis недоступен")
                return False
        except:
            print("❌ Не удалось подключиться к Redis")
            return False
        
        print("✅ Celery готов к запуску")
        return True
    
    def create_systemd_services(self):
        """Создает systemd сервисы"""
        print("⚙️ Создание systemd сервисов...")
        
        services = {
            'vashsender-celery': '''[Unit]
Description=VashSender Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory={}
Environment=DJANGO_SETTINGS_MODULE=core.settings.production
ExecStart=/usr/bin/celery -A core worker --loglevel=info --concurrency=8 --queues=email,campaigns,default
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target'''.format(self.project_root),
            
            'vashsender-flower': '''[Unit]
Description=VashSender Flower Monitor
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory={}
Environment=DJANGO_SETTINGS_MODULE=core.settings.production
ExecStart=/usr/bin/celery -A core flower --port=5555 --host=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target'''.format(self.project_root),
            
            'vashsender-gunicorn': '''[Unit]
Description=VashSender Gunicorn
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory={}
Environment=DJANGO_SETTINGS_MODULE=core.settings.production
ExecStart=/usr/local/bin/gunicorn --workers 4 --bind 0.0.0.0:8000 core.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target'''.format(self.project_root)
        }
        
        for service_name, service_content in services.items():
            service_path = f"/etc/systemd/system/{service_name}.service"
            
            try:
                with open(service_path, 'w') as f:
                    f.write(service_content)
                print(f"✅ Создан сервис {service_name}")
            except PermissionError:
                print(f"⚠️ Не удалось создать {service_name}.service (нужны права sudo)")
        
        return True
    
    def setup_nginx(self):
        """Настраивает Nginx"""
        print("🌐 Настройка Nginx...")
        
        nginx_config = '''server {
    listen 80;
    server_name vashsender.ru www.vashsender.ru;
    
    # Таймауты для больших запросов импорта
    client_max_body_size 100M;
    client_body_timeout 300s;
    client_header_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    send_timeout 300s;
    
    location /static/ {
        alias /var/www/vashsender/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /var/www/vashsender/media/;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Дополнительные таймауты для API запросов
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    location /flower/ {
        proxy_pass http://127.0.0.1:5555;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}'''
        
        try:
            with open('/etc/nginx/sites-available/vashsender', 'w') as f:
                f.write(nginx_config)
            print("✅ Конфигурация Nginx создана")
        except PermissionError:
            print("⚠️ Не удалось создать конфигурацию Nginx (нужны права sudo)")
        
        return True
    
    def run_health_check(self):
        """Запускает проверку здоровья системы"""
        print("🏥 Проверка здоровья системы...")
        
        if not self.run_command("python manage.py health_check --full", "Проверка здоровья"):
            return False
        
        return True
    
    def deploy(self):
        """Основной метод развертывания"""
        print("🚀 Развертывание VashSender на продакшене")
        print("=" * 60)
        
        steps = [
            ("Проверка предварительных требований", self.check_prerequisites),
            ("Установка зависимостей", self.install_dependencies),
            ("Настройка базы данных", self.setup_database),
            ("Настройка статических файлов", self.setup_static_files),
            ("Настройка Redis", self.setup_redis),
            ("Настройка Celery", self.setup_celery),
            ("Создание systemd сервисов", self.create_systemd_services),
            ("Настройка Nginx", self.setup_nginx),
            ("Проверка здоровья системы", self.run_health_check),
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}")
            print("-" * 40)
            
            if not step_func():
                print(f"❌ Ошибка на этапе: {step_name}")
                return False
        
        print("\n" + "=" * 60)
        print("🎉 Развертывание завершено успешно!")
        print("\n📋 Следующие шаги:")
        print("1. Настройте переменные окружения в .env файле")
        print("2. Запустите сервисы: sudo systemctl start vashsender-*")
        print("3. Включите автозапуск: sudo systemctl enable vashsender-*")
        print("4. Перезапустите Nginx: sudo systemctl restart nginx")
        print("5. Проверьте доступность: http://vashsender.ru")
        
        return True


def main():
    deployer = ProductionDeployer()
    
    if not deployer.deploy():
        print("\n❌ Развертывание не удалось")
        sys.exit(1)


if __name__ == '__main__':
    main() 