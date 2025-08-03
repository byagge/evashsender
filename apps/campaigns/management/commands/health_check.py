from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.campaigns.models import Campaign
from apps.campaigns.tasks import send_campaign
import logging
from django.db import models

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Проверяет и исправляет зависшие кампании'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Автоматически исправлять зависшие кампании',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Таймаут в минутах для определения зависшей кампании (по умолчанию 30)',
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        fix_mode = options['fix']
        
        # Находим кампании, которые "зависли" в статусе "sending"
        stuck_time = timezone.now() - timedelta(minutes=timeout_minutes)
        
        stuck_campaigns = Campaign.objects.filter(
            status=Campaign.STATUS_SENDING,
            updated_at__lt=stuck_time
        )
        
        self.stdout.write(f"Найдено {stuck_campaigns.count()} зависших кампаний (старше {timeout_minutes} минут)")
        
        if not stuck_campaigns.exists():
            self.stdout.write(self.style.SUCCESS("Зависших кампаний не найдено"))
            return
        
        for campaign in stuck_campaigns:
            self.stdout.write(f"Кампания: {campaign.name} (ID: {campaign.id})")
            self.stdout.write(f"  Статус: {campaign.status}")
            self.stdout.write(f"  Обновлена: {campaign.updated_at}")
            self.stdout.write(f"  Task ID: {campaign.celery_task_id}")
            
            if fix_mode:
                # Проверяем, сколько писем действительно отправлено
                total_recipients = campaign.contact_lists.aggregate(
                    total=models.Count('contacts')
                )['total'] or 0
                
                sent_recipients = campaign.recipients.filter(is_sent=True).count()
                
                if sent_recipients == total_recipients and total_recipients > 0:
                    # Все письма отправлены, обновляем статус на "sent"
                    campaign.status = Campaign.STATUS_SENT
                    campaign.sent_at = timezone.now()
                    campaign.celery_task_id = None
                    campaign.save(update_fields=['status', 'sent_at', 'celery_task_id'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"  Исправлено: статус обновлен на 'sent' ({sent_recipients}/{total_recipients} писем)")
                    )
                elif sent_recipients > 0:
                    # Часть писем отправлена, обновляем статус на "failed"
                    campaign.status = Campaign.STATUS_FAILED
                    campaign.celery_task_id = None
                    campaign.save(update_fields=['status', 'celery_task_id'])
                    
                    self.stdout.write(
                        self.style.WARNING(f"  Исправлено: статус обновлен на 'failed' ({sent_recipients}/{total_recipients} писем)")
                    )
                else:
                    # Ни одно письмо не отправлено, перезапускаем кампанию
                    campaign.status = Campaign.STATUS_DRAFT
                    campaign.celery_task_id = None
                    campaign.save(update_fields=['status', 'celery_task_id'])
                    
                    self.stdout.write(
                        self.style.WARNING(f"  Исправлено: статус сброшен на 'draft' для повторной отправки")
                    )
            else:
                self.stdout.write("  Используйте --fix для автоматического исправления")
            
            self.stdout.write("")
        
        if fix_mode:
            self.stdout.write(self.style.SUCCESS("Проверка и исправление завершены"))
        else:
            self.stdout.write("Для автоматического исправления используйте --fix") 