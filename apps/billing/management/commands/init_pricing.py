from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.billing.models import PlanType, Plan, BillingSettings


class Command(BaseCommand):
    help = 'Инициализация тарифных планов согласно pricing.html'

    def handle(self, *args, **options):
        self.stdout.write('Создание типов тарифов...')
        
        # Создаем типы тарифов
        plan_types = {
            'Free': {
                'name': 'Free',
                'description': 'Бесплатный тариф для начала работы'
            },
            'Subscribers': {
                'name': 'Subscribers', 
                'description': 'Тариф по количеству подписчиков'
            },
            'Letters': {
                'name': 'Letters',
                'description': 'Тариф по количеству писем'
            }
        }
        
        for plan_type_data in plan_types.values():
            plan_type, created = PlanType.objects.get_or_create(
                name=plan_type_data['name'],
                defaults=plan_type_data
            )
            if created:
                self.stdout.write(f'Создан тип тарифа: {plan_type.name}')
            else:
                self.stdout.write(f'Тип тарифа уже существует: {plan_type.name}')
        
        self.stdout.write('Создание тарифных планов...')
        
        # Получаем типы тарифов
        free_type = PlanType.objects.get(name='Free')
        subscribers_type = PlanType.objects.get(name='Subscribers')
        letters_type = PlanType.objects.get(name='Letters')
        
        # Создаем базовые тарифные планы
        base_plans_data = [
            # Бесплатный тариф
            {
                'title': 'Бесплатный',
                'plan_type': free_type,
                'subscribers': 200,
                'emails_per_month': 0,  # неограниченно
                'max_emails_per_day': 50,
                'price': 0.00,
                'discount': 0,
                'is_active': True,
                'is_featured': False,
                'sort_order': 1
            }
        ]
        
        for plan_data in base_plans_data:
            plan, created = Plan.objects.get_or_create(
                title=plan_data['title'],
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'Создан тариф: {plan.title} - {plan.price}₽')
            else:
                # Обновляем существующий тариф
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.save()
                self.stdout.write(f'Обновлен тариф: {plan.title} - {plan.price}₽')
        
        # Генерируем тарифы по подписчикам (1,000–1,000,000, с разными шагами)
        self.stdout.write('Создание тарифов по подписчикам...')
        
        # Определяем шаги для подписчиков
        subscribers_steps = [
            # Малые тарифы (1K - 10K)
            (1000, 770), (2000, 1500), (3000, 2300), (4000, 2900), (5000, 3300),
            (6000, 3700), (7000, 4100), (8000, 4500), (9000, 4700), (10000, 4900),
            # Средние тарифы (10K - 100K)
            (15000, 6500), (20000, 8000), (25000, 9500), (30000, 11000), (35000, 12500),
            (40000, 14000), (45000, 15500), (50000, 17000), (60000, 20000), (70000, 23000),
            (80000, 26000), (90000, 29000), (100000, 32000),
            # Большие тарифы (100K - 1M)
            (150000, 45000), (200000, 58000), (250000, 71000), (300000, 84000),
            (350000, 97000), (400000, 110000), (450000, 123000), (500000, 136000),
            (600000, 162000), (700000, 188000), (800000, 214000), (900000, 240000),
            (1000000, 266000)
        ]
        
        for idx, (subs, price) in enumerate(subscribers_steps, start=2):
            plan, created = Plan.objects.get_or_create(
                title=f'Подписчики {subs:,}'.replace(",", " "),
                plan_type=subscribers_type,
                defaults={
                    'subscribers': subs,
                    'emails_per_month': 0,
                    'max_emails_per_day': self._get_daily_limit(subs),
                    'price': price,
                    'discount': 0,
                    'is_active': True,
                    'is_featured': subs == 1000,  # Только 1000 подписчиков как популярный
                    'sort_order': idx
                }
            )
            if created:
                self.stdout.write(f'Создан тариф подписчиков: {subs:,} - {price}₽')
            else:
                # Обновляем существующий тариф
                plan.subscribers = subs
                plan.price = price
                plan.max_emails_per_day = self._get_daily_limit(subs)
                plan.is_featured = (subs == 1000)
                plan.sort_order = idx
                plan.save()
                self.stdout.write(f'Обновлен тариф подписчиков: {subs:,} - {price}₽')

        # Генерируем тарифы по письмам (1,000–1,000,000, с разными шагами)
        self.stdout.write('Создание тарифов по письмам...')
        
        # Определяем шаги для писем
        letters_steps = [
            # Малые пакеты (1K - 10K)
            (1000, 430), (2000, 800), (3000, 1100), (4000, 1300), (5000, 1500),
            (6000, 1700), (7000, 1900), (8000, 2100), (9000, 2300), (10000, 2500),
            # Средние пакеты (10K - 100K)
            (15000, 3500), (20000, 4500), (25000, 5500), (30000, 6500), (35000, 7500),
            (40000, 8500), (45000, 9500), (50000, 10500), (60000, 12500), (70000, 14500),
            (80000, 16500), (90000, 18500), (100000, 20500),
            # Большие пакеты (100K - 1M)
            (150000, 30000), (200000, 39500), (250000, 49000), (300000, 58500),
            (350000, 68000), (400000, 77500), (450000, 87000), (500000, 96500),
            (600000, 115500), (700000, 134500), (800000, 153500), (900000, 172500),
            (1000000, 191500)
        ]
        
        for idx, (emails, price) in enumerate(letters_steps, start=len(subscribers_steps) + 2):
            plan, created = Plan.objects.get_or_create(
                title=f'Письма {emails:,}'.replace(",", " "),
                plan_type=letters_type,
                defaults={
                    'subscribers': 0,
                    'emails_per_month': emails,
                    'max_emails_per_day': 0,  # Не применяется для тарифов с письмами
                    'price': price,
                    'discount': 0,
                    'is_active': True,
                    'is_featured': False,
                    'sort_order': idx
                }
            )
            if created:
                self.stdout.write(f'Создан тариф писем: {emails:,} - {price}₽')
            else:
                # Обновляем существующий тариф
                plan.emails_per_month = emails
                plan.price = price
                plan.sort_order = idx
                plan.save()
                self.stdout.write(f'Обновлен тариф писем: {emails:,} - {price}₽')
        
        # Создаем настройки биллинга
        self.stdout.write('Создание настроек биллинга...')
        settings, created = BillingSettings.objects.get_or_create(
            pk=1,
            defaults={
                'free_plan_subscribers': 200,
                'free_plan_emails': 0,  # неограниченно
                'free_plan_daily_limit': 50,
                'cloudpayments_test_mode': True,
                'auto_renewal_enabled': True,
                'auto_renewal_days_before': 3
            }
        )
        
        if created:
            self.stdout.write('Созданы настройки биллинга')
        else:
            self.stdout.write('Настройки биллинга уже существуют')
        
        # Выводим статистику
        total_plans = Plan.objects.count()
        subscribers_plans = Plan.objects.filter(plan_type=subscribers_type).count()
        letters_plans = Plan.objects.filter(plan_type=letters_type).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Тарифы успешно инициализированы!\n'
                f'Всего тарифов: {total_plans}\n'
                f'Тарифов по подписчикам: {subscribers_plans}\n'
                f'Тарифов по письмам: {letters_plans}'
            )
        )
    
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