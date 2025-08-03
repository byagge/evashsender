#!/usr/bin/env python
"""
Тестовый скрипт для проверки системы учёта отправленных писем
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from apps.accounts.models import User
from apps.billing.models import PurchasedPlan, Plan, PlanType
from apps.campaigns.models import Campaign, EmailTracking
from apps.billing.utils import (
    get_user_active_plan, 
    get_user_emails_remaining, 
    update_plan_emails_sent,
    get_user_plan_info,
    can_user_send_emails
)
from django.utils import timezone


def test_email_limits_system():
    """Тестирование системы учёта писем"""
    
    print("=== Тестирование системы учёта отправленных писем ===\n")
    
    # Получаем тестового пользователя
    try:
        user = User.objects.first()
        if not user:
            print("❌ Нет пользователей в системе")
            return
        print(f"👤 Тестовый пользователь: {user.email}")
    except Exception as e:
        print(f"❌ Ошибка получения пользователя: {e}")
        return
    
    # Получаем активный тариф
    active_plan = get_user_active_plan(user)
    if not active_plan:
        print("❌ У пользователя нет активного тарифа")
        return
    
    print(f"📋 Активный тариф: {active_plan.plan.title}")
    print(f"📅 Действует до: {active_plan.end_date.strftime('%Y-%m-%d')}")
    print(f"📊 Тип тарифа: {active_plan.plan.plan_type.name}")
    
    if active_plan.plan.plan_type.name == 'Letters':
        print(f"📧 Лимит писем: {active_plan.plan.emails_per_month}")
        print(f"📤 Отправлено: {active_plan.emails_sent}")
        print(f"📥 Осталось: {active_plan.get_emails_remaining()}")
    
    print()
    
    # Обновляем счётчик на основе фактических отправок
    print("🔄 Обновление счётчика на основе фактических отправок...")
    try:
        actual_sent = update_plan_emails_sent(user)
        print(f"✅ Фактически отправлено писем: {actual_sent}")
    except Exception as e:
        print(f"❌ Ошибка обновления счётчика: {e}")
    
    print()
    
    # Получаем полную информацию о тарифе
    print("📊 Полная информация о тарифе:")
    try:
        plan_info = get_user_plan_info(user)
        for key, value in plan_info.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"❌ Ошибка получения информации о тарифе: {e}")
    
    print()
    
    # Проверяем возможность отправки
    print("🔍 Проверка возможности отправки:")
    test_counts = [1, 10, 100, 1000]
    for count in test_counts:
        can_send = can_user_send_emails(user, count)
        status = "✅ Может" if can_send else "❌ Не может"
        print(f"   {count} писем: {status}")
    
    print()
    
    # Статистика кампаний пользователя
    print("📈 Статистика кампаний:")
    campaigns = Campaign.objects.filter(user=user)
    print(f"   Всего кампаний: {campaigns.count()}")
    
    total_sent = 0
    for campaign in campaigns:
        sent = campaign.emails_sent
        total_sent += sent
        print(f"   - {campaign.name}: {sent} писем")
    
    print(f"   Итого отправлено: {total_sent} писем")
    
    print()
    print("=== Тестирование завершено ===")


def test_plan_creation():
    """Тестирование создания тарифов"""
    
    print("=== Тестирование создания тарифов ===\n")
    
    # Получаем или создаём типы тарифов
    letters_type, created = PlanType.objects.get_or_create(
        name='Letters',
        defaults={'description': 'Тарифы с лимитом писем'}
    )
    subscribers_type, created = PlanType.objects.get_or_create(
        name='Subscribers', 
        defaults={'description': 'Тарифы с лимитом подписчиков'}
    )
    
    print(f"📋 Тип тарифа 'Letters': {letters_type.name}")
    print(f"📋 Тип тарифа 'Subscribers': {subscribers_type.name}")
    
    # Создаём тестовые тарифы
    test_plans = [
        {
            'title': 'Тест 100 писем',
            'plan_type': letters_type,
            'emails_per_month': 100,
            'subscribers': 0,
            'price': 0
        },
        {
            'title': 'Тест 1000 подписчиков',
            'plan_type': subscribers_type,
            'emails_per_month': 0,
            'subscribers': 1000,
            'price': 0
        }
    ]
    
    for plan_data in test_plans:
        plan, created = Plan.objects.get_or_create(
            title=plan_data['title'],
            defaults=plan_data
        )
        status = "создан" if created else "уже существует"
        print(f"📦 Тариф '{plan.title}': {status}")
    
    print()
    print("=== Создание тарифов завершено ===")


if __name__ == '__main__':
    print("🚀 Запуск тестов системы учёта писем...\n")
    
    try:
        test_plan_creation()
        print()
        test_email_limits_system()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc() 