#!/usr/bin/env python3
"""
Скрипт для тестирования отправки писем с улучшенными настройками
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.local')
django.setup()

from django.conf import settings

def test_email_sending():
    """Тестирование отправки писем с улучшенными настройками"""
    
    print("🧪 Тестирование отправки писем")
    print("=" * 50)
    
    # Тестовые данные
    test_emails = [
        "test@gmail.com",
        "test@mail.ru", 
        "test@yandex.ru"
    ]
    
    # Создаем тестовое письмо
    subject = "Тест доставляемости - VashSender"
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Тест доставляемости</title>
    </head>
    <body>
        <h2>Тест системы рассылок VashSender</h2>
        <p>Это тестовое письмо для проверки доставляемости.</p>
        <p>Если вы получили это письмо, значит настройки работают корректно.</p>
        <p>Время отправки: {time}</p>
        <hr>
        <p><small>Это письмо отправлено через систему рассылок VashSender.</small></p>
    </body>
    </html>
    """.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # Создаем plain text версию
    plain_text = """
    Тест системы рассылок VashSender
    
    Это тестовое письмо для проверки доставляемости.
    Если вы получили это письмо, значит настройки работают корректно.
    
    Время отправки: {time}
    
    ---
    Это письмо отправлено через систему рассылок VashSender.
    """.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # Настройки SMTP
    smtp_host = settings.EMAIL_HOST
    smtp_port = settings.EMAIL_PORT
    smtp_user = settings.EMAIL_HOST_USER
    smtp_pass = settings.EMAIL_HOST_PASSWORD
    use_tls = settings.EMAIL_USE_TLS
    
    print(f"SMTP Host: {smtp_host}")
    print(f"SMTP Port: {smtp_port}")
    print(f"SMTP TLS: {use_tls}")
    print(f"From: {settings.DEFAULT_FROM_EMAIL}")
    print()
    
    # Отправляем тестовые письма
    for email in test_emails:
        try:
            print(f"📧 Отправка на {email}...")
            
            # Создаем сообщение
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"VashSender <{settings.DEFAULT_FROM_EMAIL}>"
            msg['To'] = email
            msg['Reply-To'] = settings.DEFAULT_FROM_EMAIL
            
            # Добавляем улучшенные заголовки
            msg['Message-ID'] = f"<test-{datetime.now().strftime('%Y%m%d%H%M%S')}@vashsender.ru>"
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            msg['MIME-Version'] = '1.0'
            msg['X-Mailer'] = 'VashSender/1.0'
            msg['X-Priority'] = '3'
            msg['X-MSMail-Priority'] = 'Normal'
            msg['Importance'] = 'normal'
            
            # Добавляем части сообщения
            text_part = MIMEText(plain_text, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Подключаемся к SMTP
            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            
            # Устанавливаем правильный HELO
            try:
                server.helo('mail.vashsender.ru')
            except:
                pass
            
            # Авторизация если нужно
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            
            # Отправляем письмо
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Успешно отправлено на {email}")
            
        except Exception as e:
            print(f"❌ Ошибка отправки на {email}: {e}")
        
        print()
    
    print("🎯 Тестирование завершено!")
    print("\n💡 Рекомендации:")
    print("1. Проверьте входящие в указанных email адресах")
    print("2. Проверьте папку 'Спам'")
    print("3. Используйте https://www.mail-tester.com/ для детального анализа")
    print("4. Если письма в спаме, проверьте DNS настройки из EMAIL_DELIVERABILITY_FIX.md")

if __name__ == "__main__":
    test_email_sending() 