#!/usr/bin/env python
"""
Скрипт для тестирования доставляемости писем в Mail.ru
"""

import os
import sys
import django
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from django.conf import settings
from django.utils import timezone
from apps.campaigns.models import Campaign, EmailTracking
from apps.mailer.models import Contact, ContactList
from apps.mail_templates.models import EmailTemplate
from apps.emails.models import Domain, SenderEmail
from apps.campaigns.tasks import send_single_email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
import uuid


def create_test_campaign():
    """Создает тестовую кампанию для проверки доставляемости"""
    print("📧 Создание тестовой кампании...")
    
    # Получаем или создаем тестовый домен
    domain, created = Domain.objects.get_or_create(
        domain_name='vashsender.ru',
        defaults={
            'is_verified': True,
            'spf_verified': True,
            'dkim_verified': True
        }
    )
    
    # Получаем или создаем тестовый email отправителя
    sender_email, created = SenderEmail.objects.get_or_create(
        email='test@vashsender.ru',
        defaults={
            'domain': domain,
            'is_verified': True,
            'sender_name': 'VashSender Test',
            'reply_to': 'support@vashsender.ru'
        }
    )
    
    # Получаем или создаем тестовый шаблон
    template, created = EmailTemplate.objects.get_or_create(
        name='Тестовый шаблон для Mail.ru',
        defaults={
            'html_content': '''
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Тестовое письмо</title>
            </head>
            <body>
                <h1>Тестовое письмо для проверки доставляемости</h1>
                <p>Это тестовое письмо отправлено для проверки доставляемости в Mail.ru.</p>
                <p>Время отправки: {{content}}</p>
                <p>Если вы получили это письмо во входящих, значит настройки работают правильно!</p>
                <hr>
                <p><small>Отправлено через VashSender</small></p>
            </body>
            </html>
            '''
        }
    )
    
    # Получаем или создаем тестовый список контактов
    contact_list, created = ContactList.objects.get_or_create(
        name='Тестовый список для Mail.ru',
        defaults={'description': 'Список для тестирования доставляемости'}
    )
    
    # Создаем тестовый контакт
    test_email = input("Введите email для тестирования (например, ваш@mail.ru): ").strip()
    if not test_email:
        test_email = "test@mail.ru"
    
    contact, created = Contact.objects.get_or_create(
        email=test_email,
        defaults={'name': 'Тестовый контакт'}
    )
    
    # Добавляем контакт в список
    contact_list.contacts.add(contact)
    
    # Создаем тестовую кампанию
    campaign = Campaign.objects.create(
        name=f'Тест доставляемости Mail.ru {timezone.now().strftime("%Y-%m-%d %H:%M")}',
        subject='Тестовое письмо для проверки доставляемости в Mail.ru',
        content=f'Письмо отправлено {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}',
        template=template,
        sender_email=sender_email,
        sender_name='VashSender Test',
        status=Campaign.STATUS_DRAFT
    )
    
    # Добавляем список контактов к кампании
    campaign.contact_lists.add(contact_list)
    
    print(f"✅ Тестовая кампания создана: {campaign.name}")
    print(f"   Email получателя: {test_email}")
    print(f"   Отправитель: {sender_email.email}")
    
    return campaign, contact


def test_single_email_sending(campaign, contact):
    """Тестирует отправку одного письма"""
    print(f"\n📤 Тестирование отправки письма...")
    
    try:
        # Запускаем задачу отправки
        result = send_single_email.apply(args=[str(campaign.id), contact.id])
        
        print(f"✅ Задача отправки запущена: {result.id}")
        print(f"   Статус: {result.status}")
        
        # Ждем завершения
        result.get(timeout=60)
        
        print(f"✅ Письмо отправлено успешно!")
        
        # Проверяем tracking
        tracking = EmailTracking.objects.filter(campaign=campaign, contact=contact).first()
        if tracking:
            print(f"   Tracking ID: {tracking.tracking_id}")
            print(f"   Отправлено: {tracking.sent_at}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False


def test_smtp_connection():
    """Тестирует SMTP соединение"""
    print(f"\n🔌 Тестирование SMTP соединения...")
    
    try:
        # Создаем соединение
        connection = smtplib.SMTP(
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
            timeout=settings.EMAIL_CONNECTION_TIMEOUT
        )
        
        print(f"✅ SMTP соединение установлено")
        print(f"   Хост: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
        
        # Устанавливаем HELO
        try:
            connection.helo('mail.vashsender.ru')
            print(f"   HELO: mail.vashsender.ru")
        except Exception as e:
            print(f"   Ошибка HELO: {e}")
            try:
                connection.helo('localhost')
                print(f"   HELO: localhost")
            except:
                pass
        
        # Проверяем TLS
        if settings.EMAIL_USE_TLS:
            try:
                connection.starttls()
                print(f"   TLS: включен")
            except Exception as e:
                print(f"   Ошибка TLS: {e}")
        
        # Проверяем аутентификацию
        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
            try:
                connection.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                print(f"   Аутентификация: успешно")
            except Exception as e:
                print(f"   Ошибка аутентификации: {e}")
        
        connection.quit()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка SMTP соединения: {e}")
        return False


def check_email_headers_manually():
    """Проверяет заголовки писем вручную"""
    print(f"\n📋 Проверка заголовков писем...")
    
    # Создаем тестовое письмо
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Тест заголовков для Mail.ru'
    msg['From'] = formataddr(('VashSender Test', 'test@vashsender.ru'))
    msg['To'] = 'test@mail.ru'
    msg['Message-ID'] = f'<{uuid.uuid4()}@vashsender.ru>'
    msg['Date'] = timezone.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    msg['MIME-Version'] = '1.0'
    msg['X-Mailer'] = 'VashSender/1.0'
    
    # Добавляем заголовки для Mail.ru
    msg['List-Unsubscribe'] = '<mailto:unsubscribe@vashsender.ru?subject=unsubscribe>'
    msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
    msg['Precedence'] = 'bulk'
    msg['X-Auto-Response-Suppress'] = 'OOF, AutoReply'
    msg['X-Report-Abuse'] = 'Please report abuse here: abuse@vashsender.ru'
    msg['X-Sender'] = 'test@vashsender.ru'
    msg['X-Originating-IP'] = '146.185.196.123'
    msg['X-Mailer-Domain'] = 'vashsender.ru'
    
    # Добавляем содержимое
    text_content = "Это тестовое письмо для проверки заголовков."
    html_content = "<html><body><h1>Тест заголовков</h1><p>Это тестовое письмо для проверки заголовков.</p></body></html>"
    
    text_part = MIMEText(text_content, 'plain', 'utf-8')
    html_part = MIMEText(html_content, 'html', 'utf-8')
    
    msg.attach(text_part)
    msg.attach(html_part)
    
    print("✅ Заголовки письма настроены:")
    for header, value in msg.items():
        print(f"   {header}: {value}")
    
    return msg


def main():
    """Основная функция"""
    print("🚀 Тестирование доставляемости писем в Mail.ru")
    print("=" * 50)
    
    # Тестируем SMTP соединение
    if not test_smtp_connection():
        print("❌ SMTP соединение не работает. Проверьте настройки.")
        return
    
    # Проверяем заголовки
    check_email_headers_manually()
    
    # Создаем тестовую кампанию
    campaign, contact = create_test_campaign()
    
    # Тестируем отправку
    if test_single_email_sending(campaign, contact):
        print(f"\n✅ Тест завершен успешно!")
        print(f"\n📝 Инструкции для проверки:")
        print(f"1. Проверьте папку 'Входящие' в {contact.email}")
        print(f"2. Если письмо в спаме, отметьте его как 'Не спам'")
        print(f"3. Добавьте {campaign.sender_email.email} в контакты")
        print(f"4. Проверьте заголовки письма на наличие DKIM-Signature")
    else:
        print(f"\n❌ Тест не прошел. Проверьте логи ошибок.")
    
    print(f"\n📊 Статистика кампании:")
    print(f"   ID кампании: {campaign.id}")
    print(f"   Статус: {campaign.get_status_display()}")
    print(f"   Получатель: {contact.email}")


if __name__ == "__main__":
    main() 