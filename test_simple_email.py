#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_simple_email():
    """Тестируем простую отправку email"""
    
    try:
        print("=== Тест простой отправки email ===")
        print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        print(f"EMAIL_USE_SSL: {settings.EMAIL_USE_SSL}")
        print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        print()
        
        print("Отправляем тестовое письмо...")
        
        send_mail(
            'Тест восстановления пароля',
            'Это тестовое письмо для проверки работы SMTP.',
            settings.DEFAULT_FROM_EMAIL,
            ['test@example.com'],
            fail_silently=False,
        )
        
        print("✅ Простой email отправлен успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка при отправке простого email: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_simple_email() 