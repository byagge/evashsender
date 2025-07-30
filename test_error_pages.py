#!/usr/bin/env python3
"""
Скрипт для тестирования страниц ошибок vashsender
Запустите этот скрипт после настройки Django проекта
"""

import requests
import sys

def test_error_page(url, expected_status, description):
    """Тестирует страницу ошибки"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == expected_status:
            print(f"✅ {description} - OK (статус {response.status_code})")
            return True
        else:
            print(f"❌ {description} - ОШИБКА (ожидался {expected_status}, получен {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {description} - ОШИБКА СЕТИ: {e}")
        return False

def main():
    """Основная функция тестирования"""
    base_url = "http://localhost:8000"
    
    print("🧪 Тестирование страниц ошибок vashsender")
    print("=" * 50)
    
    # Список тестов
    tests = [
        ("/test/404/", 404, "404 - Страница не найдена"),
        ("/test/400/", 400, "400 - Неверный запрос"),
        ("/test/401/", 401, "401 - Требуется авторизация"),
        ("/test/403/", 403, "403 - Доступ запрещен"),
        ("/test/500/", 500, "500 - Ошибка сервера"),
        ("/test/502/", 502, "502 - Ошибка шлюза"),
        ("/test/503/", 503, "503 - Сервис недоступен"),
    ]
    
    success_count = 0
    total_tests = len(tests)
    
    for url, expected_status, description in tests:
        full_url = base_url + url
        if test_error_page(full_url, expected_status, description):
            success_count += 1
        print()
    
    print("=" * 50)
    print(f"📊 Результаты: {success_count}/{total_tests} тестов прошли успешно")
    
    if success_count == total_tests:
        print("🎉 Все страницы ошибок работают корректно!")
        return 0
    else:
        print("⚠️  Некоторые тесты не прошли. Проверьте настройки Django.")
        return 1

if __name__ == "__main__":
    print("🚀 Запуск тестирования страниц ошибок...")
    print("Убедитесь, что Django сервер запущен на http://localhost:8000")
    print("И DEBUG = False в настройках")
    print()
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        sys.exit(1) 