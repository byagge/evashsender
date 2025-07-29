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
        
        # Создаем тарифные планы согласно pricing.html
        plans_data = [
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
            },
            # Тарифы по подписчикам
            {
                'title': 'Подписчики 1,000',
                'plan_type': subscribers_type,
                'subscribers': 1000,
                'emails_per_month': 0,  # неограниченно
                'max_emails_per_day': 200,
                'price': 770.00,
                'discount': 0,
                'is_active': True,
                'is_featured': True,
                'sort_order': 2
            },
            {
                'title': 'Подписчики 5,000',
                'plan_type': subscribers_type,
                'subscribers': 5000,
                'emails_per_month': 0,  # неограниченно
                'max_emails_per_day': 500,
                'price': 2900.00,
                'discount': 0,
                'is_active': True,
                'is_featured': False,
                'sort_order': 3
            },
            {
                'title': 'Подписчики 10,000',
                'plan_type': subscribers_type,
                'subscribers': 10000,
                'emails_per_month': 0,  # неограниченно
                'max_emails_per_day': 1000,
                'price': 4900.00,
                'discount': 0,
                'is_active': True,
                'is_featured': False,
                'sort_order': 4
            },
            # Тарифы по письмам
            {
                'title': 'Письма 1,000',
                'plan_type': letters_type,
                'subscribers': 0,  # неограниченно
                'emails_per_month': 1000,
                'max_emails_per_day': 0,  # не применяется
                'price': 430.00,
                'discount': 0,
                'is_active': True,
                'is_featured': False,
                'sort_order': 5
            },
            {
                'title': 'Письма 5,000',
                'plan_type': letters_type,
                'subscribers': 0,  # неограниченно
                'emails_per_month': 5000,
                'max_emails_per_day': 0,  # не применяется
                'price': 1500.00,
                'discount': 0,
                'is_active': True,
                'is_featured': False,
                'sort_order': 6
            },
            {
                'title': 'Письма 10,000',
                'plan_type': letters_type,
                'subscribers': 0,  # неограниченно
                'emails_per_month': 10000,
                'max_emails_per_day': 0,  # не применяется
                'price': 2500.00,
                'discount': 0,
                'is_active': True,
                'is_featured': False,
                'sort_order': 7
            }
        ]
        
        for plan_data in plans_data:
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
        
        # Генерируем тарифы по подписчикам (1,000–10,000, шаг 1,000)
        subscribers_steps = [
            (1000, 770), (2000, 1500), (3000, 2300), (4000, 2900), (5000, 3300),
            (6000, 3700), (7000, 4100), (8000, 4500), (9000, 4700), (10000, 4900)
        ]
        for idx, (subs, price) in enumerate(subscribers_steps, start=2):
            Plan.objects.get_or_create(
                title=f'Подписчики {subs:,}'.replace(",", " "),
                plan_type=subscribers_type,
                defaults={
                    'subscribers': subs,
                    'emails_per_month': 0,
                    'max_emails_per_day': 200 if subs <= 1000 else 500 if subs <= 5000 else 1000,
                    'price': price,
                    'discount': 0,
                    'is_active': True,
                    'is_featured': subs == 1000,
                    'sort_order': idx
                }
            )

        # Генерируем тарифы по письмам (1,000–10,000, шаг 1,000)
        letters_steps = [
            (1000, 430), (2000, 800), (3000, 1100), (4000, 1300), (5000, 1500),
            (6000, 1700), (7000, 1900), (8000, 2100), (9000, 2300), (10000, 2500)
        ]
        for idx, (emails, price) in enumerate(letters_steps, start=20):
            Plan.objects.get_or_create(
                title=f'Письма {emails:,}'.replace(",", " "),
                plan_type=letters_type,
                defaults={
                    'subscribers': 0,
                    'emails_per_month': emails,
                    'max_emails_per_day': 0,
                    'price': price,
                    'discount': 0,
                    'is_active': True,
                    'is_featured': False,
                    'sort_order': idx
                }
            )
        
        # Создаем настройки биллинга
        self.stdout.write('Создание настроек биллинга...')
        settings, created = BillingSettings.objects.get_or_create(
            defaults={
                'free_plan_subscribers': 200,
                'free_plan_emails': 0,  # неограниченно
                'free_plan_daily_limit': 50,
                'currency': 'RUB',
                'tax_rate': 0
            }
        )
        
        if created:
            self.stdout.write('Созданы настройки биллинга')
        else:
            self.stdout.write('Настройки биллинга уже существуют')
        
        self.stdout.write(
            self.style.SUCCESS('Тарифы успешно инициализированы!')
        ) 