from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.billing.models import PlanType, Plan, BillingSettings, PurchasedPlan
from django.db import transaction


class Command(BaseCommand):
    help = 'Полный сброс и пересоздание всех тарифных планов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно удалить все тарифы без подтверждения',
        )

    def handle(self, *args, **options):
        force = options.get('force')
        
        if not force:
            self.stdout.write(
                self.style.WARNING(
                    'ВНИМАНИЕ: Эта команда удалит ВСЕ существующие тарифы и создаст новые!\n'
                    'Это может повлиять на существующих пользователей.\n'
                    'Используйте --force для подтверждения.'
                )
            )
            return
        
        with transaction.atomic():
            self.stdout.write('Удаление всех существующих тарифов...')
            
            # Удаляем все купленные тарифы
            purchased_count = PurchasedPlan.objects.count()
            PurchasedPlan.objects.all().delete()
            self.stdout.write(f'Удалено {purchased_count} купленных тарифов')
            
            # Удаляем все тарифы
            plans_count = Plan.objects.count()
            Plan.objects.all().delete()
            self.stdout.write(f'Удалено {plans_count} тарифов')
            
            # Удаляем типы тарифов
            types_count = PlanType.objects.count()
            PlanType.objects.all().delete()
            self.stdout.write(f'Удалено {types_count} типов тарифов')
            
            # Удаляем настройки биллинга
            settings_count = BillingSettings.objects.count()
            BillingSettings.objects.all().delete()
            self.stdout.write(f'Удалено {settings_count} настроек биллинга')
            
            self.stdout.write('Все данные удалены. Теперь запустите init_pricing для создания новых тарифов.')
            self.stdout.write(
                self.style.SUCCESS(
                    'Команда reset_pricing завершена успешно!\n'
                    'Запустите: python manage.py init_pricing'
                )
            ) 