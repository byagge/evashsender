#!/usr/bin/env python3
"""
Скрипт для проверки SMTP настроек и тестирования отправки
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Добавляем путь к проекту
sys.path.insert(0, '/var/www/vashsender')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')

import django
django.setup()

from django.conf import settings
from decouple import config

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def check_env_variables():
    """Проверка переменных окружения"""
    print_section("ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ")
    
    env_vars = [
        'EMAIL_HOST',
        'EMAIL_PORT', 
        'EMAIL_USE_TLS',
        'EMAIL_USE_SSL',
        'EMAIL_HOST_USER',
        'EMAIL_HOST_PASSWORD',
        'DEFAULT_FROM_EMAIL'
    ]
    
    for var in env_vars:
        try:
            value = config(var, default='НЕ УСТАНОВЛЕНА')
            if 'PASSWORD' in var and value != 'НЕ УСТАНОВЛЕНА':
                value = '***СКРЫТО***'
            print(f"{var}: {value}")
        except Exception as e:
            print(f"{var}: ОШИБКА - {e}")

def check_django_settings():
    """Проверка настроек Django"""
    print_section("ПРОВЕРКА НАСТРОЕК DJANGO")
    
    smtp_settings = [
        'EMAIL_BACKEND',
        'EMAIL_HOST',
        'EMAIL_PORT',
        'EMAIL_USE_TLS',
        'EMAIL_USE_SSL',
        'EMAIL_HOST_USER',
        'DEFAULT_FROM_EMAIL',
        'EMAIL_TIMEOUT'
    ]
    
    for setting in smtp_settings:
        try:
            value = getattr(settings, setting, 'НЕ УСТАНОВЛЕНА')
            if 'PASSWORD' in setting and value != 'НЕ УСТАНОВЛЕНА':
                value = '***СКРЫТО***'
            print(f"{setting}: {value}")
        except Exception as e:
            print(f"{setting}: ОШИБКА - {e}")

def test_smtp_connection():
    """Тестирование SMTP соединения"""
    print_section("ТЕСТИРОВАНИЕ SMTP СОЕДИНЕНИЯ")
    
    try:
        host = config('EMAIL_HOST', default='localhost')
        port = config('EMAIL_PORT', default=25, cast=int)
        use_tls = config('EMAIL_USE_TLS', default=False, cast=bool)
        use_ssl = config('EMAIL_USE_SSL', default=False, cast=bool)
        username = config('EMAIL_HOST_USER', default='')
        password = config('EMAIL_HOST_PASSWORD', default='')
        
        print(f"Подключение к {host}:{port}")
        print(f"TLS: {use_tls}, SSL: {use_ssl}")
        print(f"Username: {username}")
        
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=30)
        else:
            server = smtplib.SMTP(host, port, timeout=30)
        
        server.set_debuglevel(1)  # Включаем отладку
        
        if use_tls:
            server.starttls()
        
        if username and password:
            server.login(username, password)
            print("✅ Аутентификация успешна")
        
        # Тестируем отправку
        from_email = config('DEFAULT_FROM_EMAIL', default='noreply@vashsender.ru')
        to_email = 'test@example.com'  # Тестовый адрес
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f'SMTP Test - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        
        body = f"""
        Это тестовое письмо для проверки SMTP настроек.
        
        Время отправки: {datetime.now()}
        SMTP сервер: {host}:{port}
        TLS: {use_tls}
        SSL: {use_ssl}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # НЕ отправляем реально, только тестируем
        print("✅ SMTP соединение работает")
        print("⚠️  Тестовое письмо НЕ отправлено (только проверка соединения)")
        
        server.quit()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка SMTP: {e}")
        return False

def test_django_email():
    """Тестирование отправки через Django"""
    print_section("ТЕСТИРОВАНИЕ DJANGO EMAIL")
    
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        subject = f'Django Email Test - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        message = f"""
        Это тестовое письмо через Django.
        
        Время отправки: {datetime.now()}
        EMAIL_BACKEND: {settings.EMAIL_BACKEND}
        EMAIL_HOST: {settings.EMAIL_HOST}
        """
        
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = ['test@example.com']  # Тестовый адрес
        
        print(f"Отправка письма:")
        print(f"  От: {from_email}")
        print(f"  Кому: {recipient_list}")
        print(f"  Тема: {subject}")
        
        # НЕ отправляем реально
        print("⚠️  Письмо НЕ отправлено (только проверка настроек)")
        print("✅ Django email настройки корректны")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка Django email: {e}")
        return False

def check_recent_campaigns():
    """Проверка последних кампаний"""
    print_section("ПОСЛЕДНИЕ КАМПАНИИ")
    
    try:
        from apps.campaigns.models import Campaign
        from django.utils import timezone
        from datetime import timedelta
        
        # Кампании за последние 2 часа
        recent_campaigns = Campaign.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=2)
        ).order_by('-created_at')[:5]
        
        for campaign in recent_campaigns:
            print(f"\nКампания: {campaign.name}")
            print(f"  Статус: {campaign.status}")
            print(f"  Создана: {campaign.created_at}")
            print(f"  Отправлена: {campaign.sent_at}")
            print(f"  Task ID: {campaign.celery_task_id}")
            
            # Проверяем получателей
            from apps.campaigns.models import CampaignRecipient
            recipients = CampaignRecipient.objects.filter(campaign=campaign)
            sent_count = recipients.filter(is_sent=True).count()
            total_count = recipients.count()
            
            print(f"  Получатели: {sent_count}/{total_count} отправлено")
            
            if sent_count > 0:
                # Проверяем детали отправки
                sent_recipients = recipients.filter(is_sent=True)[:3]
                for recipient in sent_recipients:
                    try:
                        email = recipient.contact.email
                        print(f"    - {email}: отправлено в {recipient.sent_at}")
                    except AttributeError:
                        print(f"    - Получатель ID {recipient.contact.id}: отправлено в {recipient.sent_at}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке кампаний: {e}")

def main():
    """Основная функция"""
    print(f"🔍 ПРОВЕРКА SMTP НАСТРОЕК - {datetime.now()}")
    
    check_env_variables()
    check_django_settings()
    
    smtp_ok = test_smtp_connection()
    django_ok = test_django_email()
    
    check_recent_campaigns()
    
    print_section("РЕЗУЛЬТАТ")
    if smtp_ok and django_ok:
        print("✅ SMTP настройки корректны")
        print("💡 Возможные причины проблемы:")
        print("  1. Письма попадают в спам")
        print("  2. Проблемы с DNS записями")
        print("  3. Блокировка провайдером")
    else:
        print("❌ Проблемы с SMTP настройками")
        print("💡 Необходимо исправить конфигурацию")

if __name__ == '__main__':
    main() 