from django.core.management.base import BaseCommand
from apps.billing.models import PlanType, Plan


class Command(BaseCommand):
    help = 'Создает бесплатный тариф'

    def handle(self, *args, **options):
        # Получаем или создаём тип тарифа Free
        free_type, created = PlanType.objects.get_or_create(
            name='Free',
            defaults={'description': 'Бесплатный тариф для начала работы'}
        )
        
        self.stdout.write(f"📋 Тип тарифа 'Free': {free_type.name}")
        
        # Создаем бесплатный тариф
        free_plan_data = {
            'title': 'Бесплатный',
            'plan_type': free_type,
            'subscribers': 200,
            'emails_per_month': 0,  # неограниченно
            'max_emails_per_day': 50,
            'price': 0,
            'discount': 0,
            'is_active': True,
            'is_featured': False,
            'sort_order': 1
        }
        
        plan, created = Plan.objects.get_or_create(
            title=free_plan_data['title'],
            plan_type=free_plan_data['plan_type'],
            defaults=free_plan_data
        )
        
        if created:
            self.stdout.write(f"✅ Создан бесплатный тариф: {plan.title}")
        else:
            # Обновляем существующий тариф
            for key, value in free_plan_data.items():
                setattr(plan, key, value)
            plan.save()
            self.stdout.write(f"🔄 Обновлён бесплатный тариф: {plan.title}")
        
        self.stdout.write(self.style.SUCCESS("Бесплатный тариф готов к использованию!")) 