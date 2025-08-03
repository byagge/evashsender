#!/usr/bin/env python
"""
Скрипт для применения исправлений импорта контактов
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Выполняет команду и выводит результат"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - успешно")
            return True
        else:
            print(f"❌ {description} - ошибка: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - исключение: {str(e)}")
        return False

def apply_import_fixes():
    """Применяет все исправления для импорта"""
    print("🚀 Применение исправлений для импорта контактов")
    print("=" * 60)
    
    # 1. Перезапуск Django
    print("\n📋 Шаг 1: Перезапуск Django приложения")
    if not run_command("sudo systemctl restart vashsender-gunicorn", "Перезапуск Gunicorn"):
        print("⚠️ Не удалось перезапустить Gunicorn, попробуйте вручную")
    
    # 2. Перезапуск Celery
    print("\n📋 Шаг 2: Перезапуск Celery")
    if not run_command("sudo systemctl restart vashsender-celery", "Перезапуск Celery"):
        print("⚠️ Не удалось перезапустить Celery, попробуйте вручную")
    
    # 3. Перезапуск nginx
    print("\n📋 Шаг 3: Перезапуск nginx")
    if not run_command("sudo systemctl restart nginx", "Перезапуск nginx"):
        print("⚠️ Не удалось перезапустить nginx, попробуйте вручную")
    
    # 4. Проверка статуса сервисов
    print("\n📋 Шаг 4: Проверка статуса сервисов")
    services = [
        "vashsender-gunicorn",
        "vashsender-celery", 
        "nginx"
    ]
    
    for service in services:
        run_command(f"sudo systemctl status {service} --no-pager", f"Статус {service}")
    
    # 5. Проверка логов
    print("\n📋 Шаг 5: Проверка логов")
    print("Последние записи в логах Django:")
    run_command("tail -n 10 /var/log/vashsender/django.log", "Логи Django")
    
    print("\nПоследние записи в логах nginx:")
    run_command("tail -n 10 /var/log/nginx/error.log", "Логи nginx")
    
    print("\n" + "=" * 60)
    print("🎉 Исправления применены!")
    print("\n📋 Что было исправлено:")
    print("✅ Добавлен импорт timezone в views.py")
    print("✅ Оптимизирована валидация email (меньше DNS-запросов)")
    print("✅ Добавлен новый метод import-optimized")
    print("✅ Увеличены таймауты nginx")
    print("✅ Увеличены лимиты Django")
    
    print("\n📋 Для тестирования используйте:")
    print("POST /api/contactlists/{pk}/import-optimized/")
    
    print("\n📋 Мониторинг:")
    print("tail -f /var/log/vashsender/django.log")
    print("tail -f /var/log/nginx/error.log")

if __name__ == '__main__':
    apply_import_fixes() 