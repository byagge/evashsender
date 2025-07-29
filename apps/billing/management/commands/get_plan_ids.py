from django.core.management.base import BaseCommand
from apps.billing.models import Plan


class Command(BaseCommand):
    help = 'Получить ID тарифов для использования в JavaScript'

    def handle(self, *args, **options):
        self.stdout.write('ID тарифов:')
        self.stdout.write('=' * 50)
        
        plans = Plan.objects.filter(is_active=True).order_by('sort_order')
        
        for plan in plans:
            self.stdout.write(f'ID: {plan.id} | {plan.title} | {plan.plan_type.name} | {plan.price}₽')
        
        self.stdout.write('=' * 50)
        self.stdout.write('Для JavaScript используйте эти ID в функции handleChoosePlan') 