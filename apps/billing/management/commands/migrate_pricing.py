from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.billing.models import PlanType, Plan, BillingSettings, PurchasedPlan
from django.db import transaction


class Command(BaseCommand):
    help = 'Миграция существующих тарифов на новую структуру с сохранением купленных тарифов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено без внесения изменений',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        
        if dry_run:
            self.stdout.write('РЕЖИМ ПРЕДПРОСМОТРА - изменения не будут внесены')
        
        # Анализируем существующие данные
        self.stdout.write('Анализ существующих данных...')
        
        existing_plans = Plan.objects.all()
        existing_purchased = PurchasedPlan.objects.all()
        
        self.stdout.write(f'Найдено тарифов: {existing_plans.count()}')
        self.stdout.write(f'Найдено купленных тарифов: {existing_purchased.count()}')
        
        if existing_purchased.count() > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'ВНИМАНИЕ: Найдено {existing_purchased.count()} купленных тарифов!\n'
                    'Эти данные будут сохранены и привязаны к новым тарифам.'
                )
            )
        
        # Создаем маппинг старых тарифов на новые
        plan_mapping = {}
        
        for old_plan in existing_plans:
            if old_plan.plan_type.name == 'Subscribers':
                # Ищем ближайший тариф по подписчикам
                closest_plan = self._find_closest_subscribers_plan(old_plan.subscribers)
                plan_mapping[old_plan.id] = closest_plan
                self.stdout.write(f'Тариф "{old_plan.title}" -> "{closest_plan.title}"')
            elif old_plan.plan_type.name == 'Letters':
                # Ищем ближайший тариф по письмам
                closest_plan = self._find_closest_letters_plan(old_plan.emails_per_month)
                plan_mapping[old_plan.id] = closest_plan
                self.stdout.write(f'Тариф "{old_plan.title}" -> "{closest_plan.title}"')
        
        if not dry_run:
            with transaction.atomic():
                # Обновляем купленные тарифы
                updated_count = 0
                for purchased in existing_purchased:
                    if purchased.plan.id in plan_mapping:
                        new_plan = plan_mapping[purchased.plan.id]
                        purchased.plan = new_plan
                        purchased.save()
                        updated_count += 1
                        self.stdout.write(f'Обновлен купленный тариф: {purchased.user.email} -> {new_plan.title}')
                
                self.stdout.write(f'Обновлено купленных тарифов: {updated_count}')
                
                # Удаляем старые тарифы
                deleted_count = existing_plans.count()
                existing_plans.delete()
                self.stdout.write(f'Удалено старых тарифов: {deleted_count}')
                
                # Запускаем создание новых тарифов
                self.stdout.write('Создание новых тарифов...')
                from .init_pricing import Command as InitPricingCommand
                init_cmd = InitPricingCommand()
                init_cmd.handle()
        
        self.stdout.write(
            self.style.SUCCESS(
                'Миграция тарифов завершена успешно!'
            )
        )
    
    def _find_closest_subscribers_plan(self, subscribers):
        """Находит ближайший тариф по подписчикам из новых тарифов"""
        # Определяем новые тарифы по подписчикам
        new_subscribers_plans = [
            (1000, 770), (2000, 1500), (3000, 2300), (4000, 2900), (5000, 3300),
            (6000, 3700), (7000, 4100), (8000, 4500), (9000, 4700), (10000, 4900),
            (15000, 6500), (20000, 8000), (25000, 9500), (30000, 11000), (35000, 12500),
            (40000, 14000), (45000, 15500), (50000, 17000), (60000, 20000), (70000, 23000),
            (80000, 26000), (90000, 29000), (100000, 32000),
            (150000, 45000), (200000, 58000), (250000, 71000), (300000, 84000),
            (350000, 97000), (400000, 110000), (450000, 123000), (500000, 136000),
            (600000, 162000), (700000, 188000), (800000, 214000), (900000, 240000),
            (1000000, 266000)
        ]
        
        # Ищем ближайший тариф
        closest = new_subscribers_plans[0]
        min_diff = abs(subscribers - closest[0])
        
        for plan_subscribers, plan_price in new_subscribers_plans:
            diff = abs(subscribers - plan_subscribers)
            if diff < min_diff:
                min_diff = diff
                closest = (plan_subscribers, plan_price)
        
        # Создаем или получаем тариф
        plan_type = PlanType.objects.get(name='Subscribers')
        plan, created = Plan.objects.get_or_create(
            title=f'Подписчики {closest[0]:,}'.replace(",", " "),
            plan_type=plan_type,
            defaults={
                'subscribers': closest[0],
                'emails_per_month': 0,
                'max_emails_per_day': self._get_daily_limit(closest[0]),
                'price': closest[1],
                'discount': 0,
                'is_active': True,
                'is_featured': closest[0] == 1000,
                'sort_order': 1
            }
        )
        
        return plan
    
    def _find_closest_letters_plan(self, emails):
        """Находит ближайший тариф по письмам из новых тарифов"""
        # Определяем новые тарифы по письмам
        new_letters_plans = [
            (1000, 430), (2000, 800), (3000, 1100), (4000, 1300), (5000, 1500),
            (6000, 1700), (7000, 1900), (8000, 2100), (9000, 2300), (10000, 2500),
            (15000, 3500), (20000, 4500), (25000, 5500), (30000, 6500), (35000, 7500),
            (40000, 8500), (45000, 9500), (50000, 10500), (60000, 12500), (70000, 14500),
            (80000, 16500), (90000, 18500), (100000, 20500),
            (150000, 30000), (200000, 39500), (250000, 49000), (300000, 58500),
            (350000, 68000), (400000, 77500), (450000, 87000), (500000, 96500),
            (600000, 115500), (700000, 134500), (800000, 153500), (900000, 172500),
            (1000000, 191500)
        ]
        
        # Ищем ближайший тариф
        closest = new_letters_plans[0]
        min_diff = abs(emails - closest[0])
        
        for plan_emails, plan_price in new_letters_plans:
            diff = abs(emails - plan_emails)
            if diff < min_diff:
                min_diff = diff
                closest = (plan_emails, plan_price)
        
        # Создаем или получаем тариф
        plan_type = PlanType.objects.get(name='Letters')
        plan, created = Plan.objects.get_or_create(
            title=f'Письма {closest[0]:,}'.replace(",", " "),
            plan_type=plan_type,
            defaults={
                'subscribers': 0,
                'emails_per_month': closest[0],
                'max_emails_per_day': 0,
                'price': closest[1],
                'discount': 0,
                'is_active': True,
                'is_featured': False,
                'sort_order': 1
            }
        )
        
        return plan
    
    def _get_daily_limit(self, subscribers):
        """Определяет дневной лимит писем на основе количества подписчиков"""
        if subscribers <= 1000:
            return 200
        elif subscribers <= 5000:
            return 500
        elif subscribers <= 10000:
            return 1000
        elif subscribers <= 50000:
            return 2000
        elif subscribers <= 100000:
            return 5000
        elif subscribers <= 500000:
            return 10000
        else:
            return 20000 