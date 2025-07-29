from django.core.management.base import BaseCommand
from apps.support.models import TicketCategory


class Command(BaseCommand):
    help = 'Инициализация системы поддержки - создание базовых категорий тикетов'

    def handle(self, *args, **options):
        self.stdout.write('Создание категорий тикетов...')
        
        categories_data = [
            {
                'name': 'Техническая поддержка',
                'description': 'Проблемы с работой системы, ошибки, баги',
                'color': '#EF4444',
                'sort_order': 1
            },
            {
                'name': 'Биллинг и оплата',
                'description': 'Вопросы по тарифам, оплате, счетам',
                'color': '#10B981',
                'sort_order': 2
            },
            {
                'name': 'Настройка и интеграция',
                'description': 'Помощь с настройкой доменов, отправителей, интеграцией',
                'color': '#3B82F6',
                'sort_order': 3
            },
            {
                'name': 'Рассылки и кампании',
                'description': 'Вопросы по созданию и отправке рассылок',
                'color': '#8B5CF6',
                'sort_order': 4
            },
            {
                'name': 'Шаблоны писем',
                'description': 'Помощь с созданием и редактированием шаблонов',
                'color': '#F59E0B',
                'sort_order': 5
            },
            {
                'name': 'Контакты и списки',
                'description': 'Вопросы по управлению контактами и списками',
                'color': '#06B6D4',
                'sort_order': 6
            },
            {
                'name': 'Общие вопросы',
                'description': 'Общие вопросы по использованию системы',
                'color': '#6B7280',
                'sort_order': 7
            },
            {
                'name': 'Предложения и улучшения',
                'description': 'Предложения по улучшению функционала',
                'color': '#EC4899',
                'sort_order': 8
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for category_data in categories_data:
            category, created = TicketCategory.objects.get_or_create(
                name=category_data['name'],
                defaults=category_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Создана категория: {category.name}')
            else:
                # Обновляем существующую категорию
                for key, value in category_data.items():
                    setattr(category, key, value)
                category.save()
                updated_count += 1
                self.stdout.write(f'  ↻ Обновлена категория: {category.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nГотово! Создано: {created_count}, обновлено: {updated_count} категорий'
            )
        ) 