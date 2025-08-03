#!/usr/bin/env python
"""
Скрипт для диагностики проблем с Celery
"""

import os
import sys
import django
import time
import redis
from datetime import datetime

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')
django.setup()

from django.conf import settings
from apps.campaigns.models import Campaign, CampaignRecipient
from celery import current_app

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def check_celery_workers():
    """Проверка Celery workers"""
    print_header("ПРОВЕРКА CELERY WORKERS")
    
    try:
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            print("❌ Нет активных Celery workers!")
            return False
        
        print(f"✅ Найдено {len(stats)} активных workers:")
        for worker_name, worker_stats in stats.items():
            print(f"  - {worker_name}")
            print(f"    Pool: {worker_stats.get('pool', {}).get('implementation', 'unknown')}")
            print(f"    Processes: {worker_stats.get('pool', {}).get('processes', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки workers: {e}")
        return False

def check_redis_connection():
    """Проверка подключения к Redis"""
    print_header("ПРОВЕРКА REDIS")
    
    try:
        r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        print("✅ Redis подключение активно")
        
        # Проверяем очереди
        queues = ['campaigns', 'email', 'default']
        for queue in queues:
            length = r.llen(queue)
            print(f"  Очередь {queue}: {length} задач")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Redis: {e}")
        return False

def check_active_tasks():
    """Проверка активных задач"""
    print_header("АКТИВНЫЕ ЗАДАЧИ")
    
    try:
        inspect = current_app.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            print("✅ Нет активных задач")
            return
        
        total_tasks = 0
        for worker, tasks in active_tasks.items():
            print(f"Worker {worker}: {len(tasks)} задач")
            total_tasks += len(tasks)
            
            for task in tasks[:3]:  # Показываем первые 3 задачи
                task_id = task.get('id', 'unknown')
                task_name = task.get('name', 'unknown')
                task_time = task.get('time_start', 0)
                
                if task_time:
                    task_age = (time.time() - task_time) / 60
                    print(f"  - {task_name} (ID: {task_id[:8]}...) - {task_age:.1f} мин")
        
        print(f"Всего активных задач: {total_tasks}")
        
    except Exception as e:
        print(f"❌ Ошибка проверки активных задач: {e}")

def check_stuck_campaigns():
    """Проверка зависших кампаний"""
    print_header("ЗАВИСШИЕ КАМПАНИИ")
    
    from django.utils import timezone
    from datetime import timedelta
    
    # Кампании в статусе "sending" более 30 минут
    stuck_time = timezone.now() - timedelta(minutes=30)
    stuck_campaigns = Campaign.objects.filter(
        status=Campaign.STATUS_SENDING,
        updated_at__lt=stuck_time
    )
    
    if not stuck_campaigns.exists():
        print("✅ Нет зависших кампаний")
        return
    
    print(f"❌ Найдено {stuck_campaigns.count()} зависших кампаний:")
    
    for campaign in stuck_campaigns[:5]:  # Показываем первые 5
        age = (timezone.now() - campaign.updated_at).total_seconds() / 60
        print(f"  - {campaign.name} (ID: {campaign.id})")
        print(f"    Возраст: {age:.1f} минут")
        print(f"    Task ID: {campaign.celery_task_id}")
        
        # Проверяем количество отправленных писем
        sent_count = CampaignRecipient.objects.filter(
            campaign=campaign, 
            is_sent=True
        ).count()
        total_recipients = sum(cl.contacts.count() for cl in campaign.contact_lists.all())
        print(f"    Отправлено: {sent_count}/{total_recipients}")

def check_recent_campaigns():
    """Проверка недавних кампаний"""
    print_header("НЕДАВНИЕ КАМПАНИИ")
    
    from django.utils import timezone
    from datetime import timedelta
    
    # Кампании за последние 24 часа
    recent_time = timezone.now() - timedelta(hours=24)
    recent_campaigns = Campaign.objects.filter(
        created_at__gte=recent_time
    ).order_by('-created_at')[:10]
    
    if not recent_campaigns.exists():
        print("Нет кампаний за последние 24 часа")
        return
    
    print(f"Кампании за последние 24 часа:")
    
    for campaign in recent_campaigns:
        age = (timezone.now() - campaign.created_at).total_seconds() / 3600
        sent_count = CampaignRecipient.objects.filter(
            campaign=campaign, 
            is_sent=True
        ).count()
        total_recipients = sum(cl.contacts.count() for cl in campaign.contact_lists.all())
        
        status_icon = {
            'draft': '📝',
            'sending': '📤',
            'sent': '✅',
            'failed': '❌',
            'pending': '⏳'
        }.get(campaign.status, '❓')
        
        print(f"  {status_icon} {campaign.name}")
        print(f"    Статус: {campaign.status} (возраст: {age:.1f}ч)")
        print(f"    Отправлено: {sent_count}/{total_recipients}")
        if campaign.celery_task_id:
            print(f"    Task ID: {campaign.celery_task_id}")

def check_system_resources():
    """Проверка системных ресурсов"""
    print_header("СИСТЕМНЫЕ РЕСУРСЫ")
    
    try:
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"CPU: {cpu_percent}%")
        
        # Memory
        memory = psutil.virtual_memory()
        print(f"RAM: {memory.percent}% ({memory.used // 1024**3}GB / {memory.total // 1024**3}GB)")
        
        # Disk
        disk = psutil.disk_usage('/')
        print(f"Disk: {disk.percent}% ({disk.used // 1024**3}GB / {disk.total // 1024**3}GB)")
        
        # Network connections
        connections = psutil.net_connections()
        print(f"Network connections: {len(connections)}")
        
    except ImportError:
        print("psutil не установлен, пропускаем проверку ресурсов")
    except Exception as e:
        print(f"Ошибка проверки ресурсов: {e}")

def main():
    """Основная функция диагностики"""
    print(f"🔍 ДИАГНОСТИКА CELERY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверяем базовые компоненты
    redis_ok = check_redis_connection()
    workers_ok = check_celery_workers()
    
    if not redis_ok or not workers_ok:
        print("\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ!")
        print("Рекомендации:")
        if not redis_ok:
            print("- Проверьте, что Redis запущен")
        if not workers_ok:
            print("- Перезапустите Celery workers")
        return
    
    # Дополнительные проверки
    check_active_tasks()
    check_stuck_campaigns()
    check_recent_campaigns()
    check_system_resources()
    
    print("\n✅ Диагностика завершена")

if __name__ == '__main__':
    main() 