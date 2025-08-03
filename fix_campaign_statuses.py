#!/usr/bin/env python3
"""
Скрипт для проверки и исправления статусов кампаний
"""

import os
import sys
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.insert(0, '/var/www/vashsender')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')

import django
django.setup()

from django.utils import timezone
from django.db import transaction
from apps.campaigns.models import Campaign, CampaignRecipient

def print_section(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def check_campaign_statuses():
    """Проверка статусов кампаний"""
    print_section("ПРОВЕРКА СТАТУСОВ КАМПАНИЙ")
    
    # Кампании за последние 24 часа
    recent_campaigns = Campaign.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-created_at')
    
    print(f"Найдено {recent_campaigns.count()} кампаний за последние 24 часа")
    
    for campaign in recent_campaigns:
        print(f"\n📧 Кампания: {campaign.name}")
        print(f"   ID: {campaign.id}")
        print(f"   Статус: {campaign.status}")
        print(f"   Создана: {campaign.created_at}")
        print(f"   Отправлена: {campaign.sent_at}")
        print(f"   Task ID: {campaign.celery_task_id}")
        
        # Проверяем получателей
        recipients = CampaignRecipient.objects.filter(campaign=campaign)
        sent_count = recipients.filter(is_sent=True).count()
        failed_count = recipients.filter(is_sent=False).count()
        total_count = recipients.count()
        
        print(f"   Получатели: {sent_count} отправлено, {failed_count} неудачно, {total_count} всего")
        
        # Проверяем соответствие статуса и реального состояния
        if campaign.status == 'sent' and sent_count == 0:
            print(f"   ⚠️  ПРОБЛЕМА: Статус 'sent', но нет отправленных писем")
        elif campaign.status == 'sending' and total_count > 0 and (sent_count + failed_count) >= total_count:
            print(f"   ⚠️  ПРОБЛЕМА: Статус 'sending', но все письма обработаны")
        elif campaign.status == 'draft' and total_count > 0:
            print(f"   ⚠️  ПРОБЛЕМА: Статус 'draft', но есть получатели")

def fix_campaign_statuses():
    """Исправление статусов кампаний"""
    print_section("ИСПРАВЛЕНИЕ СТАТУСОВ КАМПАНИЙ")
    
    with transaction.atomic():
        # Находим кампании с неправильными статусами
        campaigns_to_fix = []
        
        recent_campaigns = Campaign.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        for campaign in recent_campaigns:
            recipients = CampaignRecipient.objects.filter(campaign=campaign)
            sent_count = recipients.filter(is_sent=True).count()
            failed_count = recipients.filter(is_sent=False).count()
            total_count = recipients.count()
            
            # Определяем правильный статус
            correct_status = None
            
            if total_count == 0:
                correct_status = 'draft'
            elif (sent_count + failed_count) >= total_count:
                if failed_count == 0 and sent_count > 0:
                    correct_status = 'sent'
                elif failed_count > 0:
                    correct_status = 'failed'
                else:
                    correct_status = 'draft'
            else:
                correct_status = 'sending'
            
            # Если статус неправильный, добавляем в список для исправления
            if campaign.status != correct_status:
                campaigns_to_fix.append({
                    'campaign': campaign,
                    'old_status': campaign.status,
                    'new_status': correct_status,
                    'sent_count': sent_count,
                    'failed_count': failed_count,
                    'total_count': total_count
                })
        
        print(f"Найдено {len(campaigns_to_fix)} кампаний для исправления")
        
        # Исправляем статусы
        for fix_data in campaigns_to_fix:
            campaign = fix_data['campaign']
            old_status = fix_data['old_status']
            new_status = fix_data['new_status']
            
            print(f"\n🔧 Исправление кампании: {campaign.name}")
            print(f"   Старый статус: {old_status}")
            print(f"   Новый статус: {new_status}")
            print(f"   Статистика: {fix_data['sent_count']}/{fix_data['total_count']} отправлено")
            
            # Обновляем статус
            campaign.status = new_status
            
            # Если статус 'sent', устанавливаем sent_at
            if new_status == 'sent' and not campaign.sent_at:
                campaign.sent_at = timezone.now()
            
            campaign.save(update_fields=['status', 'sent_at'])
            
            print(f"   ✅ Статус обновлен")

def check_email_delivery():
    """Проверка доставки писем"""
    print_section("ПРОВЕРКА ДОСТАВКИ ПИСЕМ")
    
    # Проверяем последние отправленные письма
    recent_recipients = CampaignRecipient.objects.filter(
        is_sent=True,
        sent_at__gte=timezone.now() - timedelta(hours=2)
    ).order_by('-sent_at')[:10]
    
    print(f"Последние 10 отправленных писем:")
    
    for recipient in recent_recipients:
        print(f"\n📨 Получатель: {recipient.contact.email}")
        print(f"   Кампания: {recipient.campaign.name}")
        print(f"   Отправлено: {recipient.sent_at}")
        print(f"   Статус кампании: {recipient.campaign.status}")

def main():
    """Основная функция"""
    print(f"🔍 ПРОВЕРКА И ИСПРАВЛЕНИЕ СТАТУСОВ КАМПАНИЙ - {datetime.now()}")
    
    check_campaign_statuses()
    
    response = input("\nХотите исправить статусы кампаний? (y/n): ")
    if response.lower() == 'y':
        fix_campaign_statuses()
    
    check_email_delivery()
    
    print_section("РЕЗУЛЬТАТ")
    print("✅ Проверка завершена")
    print("💡 Если письма не доходят, проверьте:")
    print("   1. Логи Postfix: tail -f /var/log/mail.log")
    print("   2. DNS записи домена vashsender.ru")
    print("   3. Блокировку IP сервера провайдерами")

if __name__ == '__main__':
    main() 