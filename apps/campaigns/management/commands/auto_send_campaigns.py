from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.campaigns.models import Campaign
from apps.campaigns.views import CampaignViewSet

class Command(BaseCommand):
    help = 'Автоматически отправляет кампании, которые прошли время ожидания модерации'

    def handle(self, *args, **options):
        self.stdout.write('Проверяем кампании для автоматической отправки...')
        
        # Находим кампании со статусом pending, у которых прошло время auto_send_at
        campaigns_to_send = Campaign.objects.filter(
            status='pending',
            auto_send_at__lte=timezone.now()
        )
        
        if not campaigns_to_send.exists():
            self.stdout.write('Нет кампаний для автоматической отправки')
            return
        
        self.stdout.write(f'Найдено {campaigns_to_send.count()} кампаний для отправки')
        
        viewset = CampaignViewSet()
        success_count = 0
        error_count = 0
        
        for campaign in campaigns_to_send:
            try:
                self.stdout.write(f'Отправляем кампанию: {campaign.name} (ID: {campaign.id})')
                
                # Меняем статус на sending
                campaign.status = 'sending'
                campaign.save()
                
                # Отправляем кампанию
                viewset._send_sync(campaign)
                
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Кампания {campaign.name} успешно отправлена')
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при отправке кампании {campaign.name}: {e}')
                )
                # Меняем статус на failed
                campaign.status = 'failed'
                campaign.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Автоматическая отправка завершена. Успешно: {success_count}, Ошибок: {error_count}'
            )
        ) 