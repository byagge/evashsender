from django.core.management.base import BaseCommand
from apps.billing.models import Plan, PlanType, BillingSettings


class Command(BaseCommand):
    help = 'Создает базовые тарифные планы'

    def handle(self, *args, **options):
        # Получаем настройки биллинга
        settings = BillingSettings.get_settings()
        
        # Получаем типы планов
        free_type = PlanType.objects.get(id=1)  # Free
        subscribers_type = PlanType.objects.get(id=2)  # Subscribers
        letters_type = PlanType.objects.get(id=3)  # Letters
        
        # Создаем бесплатный план
        free_plan, created = Plan.objects.get_or_create(
            title="Бесплатный",
            defaults={
                'plan_type': free_type,
                'subscribers': settings.free_plan_subscribers,
                'emails_per_month': settings.free_plan_emails,
                'max_emails_per_day': settings.free_plan_daily_limit,
                'price': 0,
                'sort_order': 1
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Создан бесплатный план: {free_plan}'))
        else:
            self.stdout.write(f'Бесплатный план уже существует: {free_plan}')
        
        # Создаем планы по подписчикам
        subscriber_plans = [
            {
                'title': 'Старт',
                'plan_type': subscribers_type,
                'subscribers': 1000,
                'emails_per_month': 5000,
                'max_emails_per_day': 200,
                'price': 299,
                'sort_order': 2
            },
            {
                'title': 'Бизнес',
                'plan_type': subscribers_type,
                'subscribers': 5000,
                'emails_per_month': 25000,
                'max_emails_per_day': 1000,
                'price': 799,
                'sort_order': 3
            },
            {
                'title': 'Про',
                'plan_type': subscribers_type,
                'subscribers': 10000,
                'emails_per_month': 50000,
                'max_emails_per_day': 2000,
                'price': 1499,
                'sort_order': 4
            }
        ]
        
        for plan_data in subscriber_plans:
            plan, created = Plan.objects.get_or_create(
                title=plan_data['title'],
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан план: {plan}'))
            else:
                self.stdout.write(f'План уже существует: {plan}')
        
        # Создаем планы по письмам
        letter_plans = [
            {
                'title': 'Базовый',
                'plan_type': letters_type,
                'subscribers': 1000,
                'emails_per_month': 10000,
                'max_emails_per_day': 500,
                'price': 199,
                'sort_order': 5
            },
            {
                'title': 'Расширенный',
                'plan_type': letters_type,
                'subscribers': 5000,
                'emails_per_month': 50000,
                'max_emails_per_day': 2500,
                'price': 499,
                'sort_order': 6
            }
        ]
        
        for plan_data in letter_plans:
            plan, created = Plan.objects.get_or_create(
                title=plan_data['title'],
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан план: {plan}'))
            else:
                self.stdout.write(f'План уже существует: {plan}')
        
        self.stdout.write(self.style.SUCCESS('Все тарифные планы созданы успешно!')) 