#!/usr/bin/env python
"""
Тестовый скрипт для проверки расширенных тарифов
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from apps.billing.models import Plan, PlanType
from apps.billing.utils import get_user_plan_info, can_user_send_emails
from apps.accounts.models import User


def test_plans_creation():
    """Тестирование создания тарифов"""
    print("🔍 Проверка создания тарифов...")
    
    # Проверяем типы тарифов
    plan_types = PlanType.objects.all()
    print(f"📋 Найдено типов тарифов: {plan_types.count()}")
    for pt in plan_types:
        print(f"  - {pt.name}: {pt.description}")
    
    # Проверяем тарифы
    plans = Plan.objects.filter(is_active=True).order_by('sort_order')
    print(f"\n📊 Найдено активных тарифов: {plans.count()}")
    
    for plan in plans:
        if plan.plan_type.name == 'Letters':
            limit = f"{plan.emails_per_month:,} писем"
        elif plan.plan_type.name == 'Subscribers':
            limit = f"{plan.subscribers:,} подписчиков"
        else:
            limit = f"{plan.subscribers} подписчиков, неограниченные письма"
        
        print(f"  - {plan.title}: {limit} - {plan.price}₽ (ID: {plan.id})")
    
    return plans.count() > 0


def test_plan_search():
    """Тестирование поиска тарифов"""
    print("\n🔍 Тестирование поиска тарифов...")
    
    # Тестируем поиск тарифов по подписчикам
    subscribers_plans = Plan.objects.filter(
        plan_type__name='Subscribers',
        is_active=True
    ).order_by('subscribers')
    
    test_values = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]
    
    for value in test_values:
        # Ищем подходящий тариф
        suitable_plan = None
        min_difference = float('inf')
        
        for plan in subscribers_plans:
            if plan.subscribers >= value:
                difference = plan.subscribers - value
                if difference < min_difference:
                    min_difference = difference
                    suitable_plan = plan
        
        if suitable_plan:
            print(f"  {value:,} подписчиков → {suitable_plan.title} ({suitable_plan.subscribers:,})")
        else:
            print(f"  {value:,} подписчиков → не найден подходящий тариф")
    
    # Тестируем поиск тарифов по письмам
    letters_plans = Plan.objects.filter(
        plan_type__name='Letters',
        is_active=True
    ).order_by('emails_per_month')
    
    test_emails = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]
    
    print("\n📧 Поиск тарифов по письмам:")
    for value in test_emails:
        # Ищем подходящий тариф
        suitable_plan = None
        min_difference = float('inf')
        
        for plan in letters_plans:
            if plan.emails_per_month >= value:
                difference = plan.emails_per_month - value
                if difference < min_difference:
                    min_difference = difference
                    suitable_plan = plan
        
        if suitable_plan:
            print(f"  {value:,} писем → {suitable_plan.title} ({suitable_plan.emails_per_month:,})")
        else:
            print(f"  {value:,} писем → не найден подходящий тариф")


def test_user_plan_info():
    """Тестирование информации о тарифе пользователя"""
    print("\n👤 Тестирование информации о тарифе пользователя...")
    
    # Получаем первого пользователя для тестирования
    try:
        user = User.objects.first()
        if not user:
            print("  ❌ Пользователи не найдены")
            return
        
        print(f"  Тестируем для пользователя: {user.email}")
        
        # Получаем информацию о тарифе
        plan_info = get_user_plan_info(user)
        
        print(f"  Есть тариф: {plan_info.get('has_plan', False)}")
        if plan_info.get('has_plan'):
            print(f"  Название тарифа: {plan_info.get('plan_name')}")
            print(f"  Тип тарифа: {plan_info.get('plan_type')}")
            print(f"  Лимит писем: {plan_info.get('emails_limit')}")
            print(f"  Отправлено писем: {plan_info.get('emails_sent')}")
            print(f"  Осталось писем: {plan_info.get('emails_remaining')}")
            print(f"  Дней осталось: {plan_info.get('days_remaining')}")
            print(f"  Истек: {plan_info.get('is_expired')}")
        
        # Тестируем проверку возможности отправки
        test_counts = [1, 10, 100, 1000]
        for count in test_counts:
            can_send = can_user_send_emails(user, count)
            print(f"  Можно отправить {count} писем: {can_send}")
            
    except Exception as e:
        print(f"  ❌ Ошибка при тестировании: {e}")


def test_pricing_calculation():
    """Тестирование расчета цен"""
    print("\n💰 Тестирование расчета цен...")
    
    # Тестируем интерполяцию цен для подписчиков
    subscribers_plans = Plan.objects.filter(
        plan_type__name='Subscribers',
        is_active=True
    ).order_by('subscribers')
    
    test_values = [1500, 3000, 7500, 15000, 75000, 150000, 750000]
    
    for value in test_values:
        # Находим ближайшие тарифы
        lower_plan = None
        upper_plan = None
        
        for plan in subscribers_plans:
            if plan.subscribers <= value:
                lower_plan = plan
            if plan.subscribers >= value and not upper_plan:
                upper_plan = plan
        
        if lower_plan and upper_plan:
            # Интерполируем цену
            ratio = (value - lower_plan.subscribers) / (upper_plan.subscribers - lower_plan.subscribers)
            interpolated_price = lower_plan.price + (upper_plan.price - lower_plan.price) * ratio
            
            print(f"  {value:,} подписчиков → {interpolated_price:.0f}₽ "
                  f"({lower_plan.subscribers:,}₽ - {upper_plan.subscribers:,}₽)")
        else:
            print(f"  {value:,} подписчиков → не удалось рассчитать")


def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование расширенных тарифов")
    print("=" * 50)
    
    # Тест 1: Создание тарифов
    if not test_plans_creation():
        print("❌ Ошибка: тарифы не созданы")
        return
    
    # Тест 2: Поиск тарифов
    test_plan_search()
    
    # Тест 3: Информация о тарифе пользователя
    test_user_plan_info()
    
    # Тест 4: Расчет цен
    test_pricing_calculation()
    
    print("\n" + "=" * 50)
    print("✅ Тестирование завершено!")


if __name__ == "__main__":
    main() 