#!/usr/bin/env python
"""
Тестовый скрипт для проверки оптимизированного импорта контактов
"""

import os
import sys
import django
from django.conf import settings

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')
django.setup()

from apps.mailer.models import ContactList, Contact, ImportTask
from apps.mailer.utils import parse_emails, validate_email_fast
from django.contrib.auth import get_user_model

User = get_user_model()

def create_test_file(filename, num_emails=1000):
    """Создает тестовый файл с email адресами"""
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'test.com']
    
    with open(filename, 'w') as f:
        for i in range(num_emails):
            email = f"test{i}@{domains[i % len(domains)]}"
            f.write(f"{email}\n")
    
    print(f"Создан тестовый файл {filename} с {num_emails} email адресами")

def test_import_performance():
    """Тестирует производительность импорта"""
    # Создаем тестового пользователя
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com'}
    )
    
    # Создаем тестовый список контактов
    contact_list, created = ContactList.objects.get_or_create(
        owner=user,
        name='Test Import List',
        defaults={}
    )
    
    # Создаем тестовый файл
    test_file = 'test_emails.txt'
    create_test_file(test_file, 1000)
    
    print(f"Тестируем импорт {1000} контактов...")
    
    # Имитируем процесс импорта
    with open(test_file, 'rb') as f:
        emails = parse_emails(f, test_file)
    
    print(f"Прочитано {len(emails)} email адресов")
    
    # Тестируем валидацию
    valid_count = 0
    invalid_count = 0
    
    for email in emails[:100]:  # Тестируем первые 100
        result = validate_email_fast(email)
        if result['is_valid']:
            valid_count += 1
        else:
            invalid_count += 1
    
    print(f"Валидация: {valid_count} валидных, {invalid_count} невалидных")
    
    # Очистка
    os.remove(test_file)
    print("Тест завершен")

if __name__ == '__main__':
    test_import_performance() 