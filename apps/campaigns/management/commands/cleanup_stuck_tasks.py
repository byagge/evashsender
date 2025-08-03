from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.campaigns.models import Campaign
from celery import current_app
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Очищает зависшие задачи Celery и кампании'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно очистить все зависшие задачи',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Таймаут в минутах для определения зависшей задачи (по умолчанию 30)',
        )

    def handle(self, *args, **options):
        timeout_minutes = options['timeout']
        force_mode = options['force']
        
        self.stdout.write(f"Очистка зависших задач (таймаут: {timeout_minutes} минут)")
        
        # 1. Очищаем зависшие кампании
        self.cleanup_stuck_campaigns(timeout_minutes, force_mode)
        
        # 2. Очищаем зависшие задачи Celery
        self.cleanup_stuck_celery_tasks(timeout_minutes, force_mode)
        
        # 3. Очищаем очереди
        self.cleanup_queues(force_mode)
        
        self.stdout.write(self.style.SUCCESS("Очистка завершена"))

    def cleanup_stuck_campaigns(self, timeout_minutes, force_mode):
        """Очистка зависших кампаний"""
        stuck_time = timezone.now() - timedelta(minutes=timeout_minutes)
        
        stuck_campaigns = Campaign.objects.filter(
            status=Campaign.STATUS_SENDING,
            updated_at__lt=stuck_time
        )
        
        self.stdout.write(f"Найдено {stuck_campaigns.count()} зависших кампаний")
        
        for campaign in stuck_campaigns:
            self.stdout.write(f"  Кампания: {campaign.name} (ID: {campaign.id})")
            
            if force_mode:
                # Сбрасываем статус в черновик
                campaign.status = Campaign.STATUS_DRAFT
                campaign.celery_task_id = None
                campaign.save(update_fields=['status', 'celery_task_id'])
                
                self.stdout.write(self.style.SUCCESS(f"    Сброшена в черновик"))
            else:
                self.stdout.write("    Используйте --force для сброса")

    def cleanup_stuck_celery_tasks(self, timeout_minutes, force_mode):
        """Очистка зависших задач Celery"""
        try:
            inspect = current_app.control.inspect()
            
            # Получаем активные задачи
            active_tasks = inspect.active()
            
            if not active_tasks:
                self.stdout.write("Нет активных задач Celery")
                return
            
            stuck_tasks = []
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    # Проверяем время начала задачи
                    task_start = task.get('time_start', 0)
                    if task_start:
                        task_age = (timezone.now().timestamp() - task_start) / 60
                        if task_age > timeout_minutes:
                            stuck_tasks.append((worker, task))
            
            self.stdout.write(f"Найдено {len(stuck_tasks)} зависших задач Celery")
            
            if force_mode and stuck_tasks:
                for worker, task in stuck_tasks:
                    task_id = task['id']
                    task_name = task['name']
                    
                    self.stdout.write(f"  Задача: {task_name} (ID: {task_id}) на {worker}")
                    
                    try:
                        # Отзываем задачу
                        current_app.control.revoke(task_id, terminate=True)
                        self.stdout.write(self.style.SUCCESS(f"    Отозвана"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"    Ошибка отзыва: {e}"))
            elif stuck_tasks:
                for worker, task in stuck_tasks:
                    task_id = task['id']
                    task_name = task['name']
                    self.stdout.write(f"  Задача: {task_name} (ID: {task_id}) на {worker}")
                    self.stdout.write("    Используйте --force для отзыва")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при очистке задач Celery: {e}"))

    def cleanup_queues(self, force_mode):
        """Очистка очередей"""
        try:
            from django.conf import settings
            import redis
            
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            
            queues = ['campaigns', 'email', 'default']
            
            for queue in queues:
                try:
                    queue_length = r.llen(queue)
                    self.stdout.write(f"Очередь {queue}: {queue_length} задач")
                    
                    if force_mode and queue_length > 0:
                        # Очищаем очередь
                        r.delete(queue)
                        self.stdout.write(self.style.SUCCESS(f"  Очередь {queue} очищена"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Ошибка при работе с очередью {queue}: {e}"))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка при очистке очередей: {e}")) 