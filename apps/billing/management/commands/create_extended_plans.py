from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.billing.models import PlanType, Plan


class Command(BaseCommand):
    help = 'Создает расширенные тарифные планы с лимитами до 1 млн писем/подписчиков'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительно пересоздать все тарифы',
        )

    def handle(self, *args, **options):
        force = options.get('force')
        
        # Получаем или создаём типы тарифов
        letters_type, created = PlanType.objects.get_or_create(
            name='Letters',
            defaults={'description': 'Тарифы с лимитом писем'}
        )
        subscribers_type, created = PlanType.objects.get_or_create(
            name='Subscribers', 
            defaults={'description': 'Тарифы с лимитом подписчиков'}
        )
        
        self.stdout.write(f"📋 Тип тарифа 'Letters': {letters_type.name}")
        self.stdout.write(f"📋 Тип тарифа 'Subscribers': {subscribers_type.name}")
        
        # Тарифы с лимитом писем
        letters_plans = [
            {
                'title': 'Письма 1,000',
                'plan_type': letters_type,
                'emails_per_month': 1000,
                'subscribers': 0,
                'max_emails_per_day': 200,
                'price': 430,
                'discount': 0,
                'is_featured': False,
                'sort_order': 1
            },
            {
                'title': 'Письма 2,000',
                'plan_type': letters_type,
                'emails_per_month': 2000,
                'subscribers': 0,
                'max_emails_per_day': 400,
                'price': 800,
                'discount': 0,
                'is_featured': False,
                'sort_order': 2
            },
            {
                'title': 'Письма 5,000',
                'plan_type': letters_type,
                'emails_per_month': 5000,
                'subscribers': 0,
                'max_emails_per_day': 1000,
                'price': 1500,
                'discount': 0,
                'is_featured': False,
                'sort_order': 3
            },
            {
                'title': 'Письма 10,000',
                'plan_type': letters_type,
                'emails_per_month': 10000,
                'subscribers': 0,
                'max_emails_per_day': 2000,
                'price': 2500,
                'discount': 0,
                'is_featured': True,
                'sort_order': 4
            },
            {
                'title': 'Письма 25,000',
                'plan_type': letters_type,
                'emails_per_month': 25000,
                'subscribers': 0,
                'max_emails_per_day': 5000,
                'price': 5500,
                'discount': 0,
                'is_featured': False,
                'sort_order': 5
            },
            {
                'title': 'Письма 50,000',
                'plan_type': letters_type,
                'emails_per_month': 50000,
                'subscribers': 0,
                'max_emails_per_day': 10000,
                'price': 9999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 6
            },
            {
                'title': 'Письма 100,000',
                'plan_type': letters_type,
                'emails_per_month': 100000,
                'subscribers': 0,
                'max_emails_per_day': 20000,
                'price': 17999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 7
            },
            {
                'title': 'Письма 250,000',
                'plan_type': letters_type,
                'emails_per_month': 250000,
                'subscribers': 0,
                'max_emails_per_day': 50000,
                'price': 39999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 8
            },
            {
                'title': 'Письма 500,000',
                'plan_type': letters_type,
                'emails_per_month': 500000,
                'subscribers': 0,
                'max_emails_per_day': 100000,
                'price': 69999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 9
            },
            {
                'title': 'Письма 1,000,000',
                'plan_type': letters_type,
                'emails_per_month': 1000000,
                'subscribers': 0,
                'max_emails_per_day': 200000,
                'price': 129999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 10
            }
        ]
        
        # Тарифы с лимитом подписчиков
        subscribers_plans = [
            {
                'title': 'Подписчики 1,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 1000,
                'max_emails_per_day': 200,
                'price': 770,
                'discount': 0,
                'is_featured': False,
                'sort_order': 1
            },
            {
                'title': 'Подписчики 2,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 2000,
                'max_emails_per_day': 400,
                'price': 1500,
                'discount': 0,
                'is_featured': False,
                'sort_order': 2
            },
            {
                'title': 'Подписчики 5,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 5000,
                'max_emails_per_day': 1000,
                'price': 2900,
                'discount': 0,
                'is_featured': False,
                'sort_order': 3
            },
            {
                'title': 'Подписчики 10,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 10000,
                'max_emails_per_day': 2000,
                'price': 4900,
                'discount': 0,
                'is_featured': True,
                'sort_order': 4
            },
            {
                'title': 'Подписчики 25,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 25000,
                'max_emails_per_day': 5000,
                'price': 9999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 5
            },
            {
                'title': 'Подписчики 50,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 50000,
                'max_emails_per_day': 10000,
                'price': 17999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 6
            },
            {
                'title': 'Подписчики 100,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 100000,
                'max_emails_per_day': 20000,
                'price': 29999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 7
            },
            {
                'title': 'Подписчики 250,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 250000,
                'max_emails_per_day': 50000,
                'price': 54999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 8
            },
            {
                'title': 'Подписчики 500,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 500000,
                'max_emails_per_day': 100000,
                'price': 99999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 9
            },
            {
                'title': 'Подписчики 1,000,000',
                'plan_type': subscribers_type,
                'emails_per_month': 0,
                'subscribers': 1000000,
                'max_emails_per_day': 200000,
                'price': 179999,
                'discount': 0,
                'is_featured': False,
                'sort_order': 10
            }
        ]
        
        all_plans = letters_plans + subscribers_plans
        created_count = 0
        updated_count = 0
        
        for plan_data in all_plans:
            plan, created = Plan.objects.get_or_create(
                title=plan_data['title'],
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"✅ Создан тариф: {plan.title} - {plan.price}₽")
            else:
                if force:
                    # Обновляем существующий тариф
                    for key, value in plan_data.items():
                        setattr(plan, key, value)
                    plan.save()
                    updated_count += 1
                    self.stdout.write(f"🔄 Обновлён тариф: {plan.title} - {plan.price}₽")
                else:
                    self.stdout.write(f"⏭️  Тариф уже существует: {plan.title}")
        
        self.stdout.write(self.style.SUCCESS(
            f"\n📊 Итого: создано {created_count}, обновлено {updated_count} тарифов"
        ))
        
        # Показываем статистику
        self.stdout.write("\n📈 Статистика тарифов:")
        for plan_type in [letters_type, subscribers_type]:
            plans = Plan.objects.filter(plan_type=plan_type, is_active=True).order_by('sort_order')
            self.stdout.write(f"\n{plan_type.name}:")
            for plan in plans:
                if plan.plan_type.name == 'Letters':
                    limit = f"{plan.emails_per_month:,} писем"
                else:
                    limit = f"{plan.subscribers:,} подписчиков"
                self.stdout.write(f"  - {plan.title}: {limit} - {plan.price}₽") 