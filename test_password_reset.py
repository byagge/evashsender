#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')
django.setup()

from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm

User = get_user_model()

def test_password_reset_email():
    """Тестируем отправку email для восстановления пароля"""
    
    # Находим пользователя для тестирования
    try:
        user = User.objects.first()
        if not user:
            print("Нет пользователей в базе данных")
            return
        
        print(f"Тестируем с пользователем: {user.email}")
        
        # Создаем форму восстановления пароля
        form = PasswordResetForm({'email': user.email})
        
        if form.is_valid():
            print("Форма валидна, отправляем email...")
            
            # Отправляем email
            form.save(
                request=None,
                use_https=True,
                from_email='noreply@vashsender.ru',
                email_template_name='password_reset_email.html',
                subject_template_name='password_reset_subject.txt'
            )
            
            print("Email отправлен успешно!")
        else:
            print("Ошибки в форме:", form.errors)
            
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")
        import traceback
        traceback.print_exc()

def test_simple_email():
    """Тестируем простую отправку email"""
    
    try:
        print("Тестируем простую отправку email...")
        
        send_mail(
            'Тест восстановления пароля',
            'Это тестовое письмо для проверки работы SMTP.',
            'noreply@vashsender.ru',
            ['test@example.com'],
            fail_silently=False,
        )
        
        print("Простой email отправлен успешно!")
        
    except Exception as e:
        print(f"Ошибка при отправке простого email: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=== Тест восстановления пароля ===")
    test_simple_email()
    print("\n=== Тест формы восстановления пароля ===")
    test_password_reset_email() 