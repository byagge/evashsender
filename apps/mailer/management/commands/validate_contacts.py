from django.core.management.base import BaseCommand
from apps.mailer.models import Contact
from apps.mailer.utils import validate_email_production
from django.db import transaction


class Command(BaseCommand):
    help = 'Валидирует все существующие контакты и обновляет их статусы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено без сохранения',
        )
        parser.add_argument(
            '--list-id',
            type=int,
            help='Валидировать только контакты из конкретного списка',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        list_id = options.get('list_id')
        
        # Получаем контакты для валидации
        if list_id:
            contacts = Contact.objects.filter(contact_list_id=list_id)
            self.stdout.write(f"Валидация контактов из списка ID: {list_id}")
        else:
            contacts = Contact.objects.all()
            self.stdout.write("Валидация всех контактов")
        
        total_contacts = contacts.count()
        self.stdout.write(f"Всего контактов для валидации: {total_contacts}")
        
        if dry_run:
            self.stdout.write("РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА - изменения не будут сохранены")
        
        # Статистика
        stats = {
            'valid': 0,
            'invalid': 0,
            'blacklist': 0,
            'unchanged': 0,
            'changed': 0
        }
        
        # Валидируем контакты
        for i, contact in enumerate(contacts, 1):
            if i % 100 == 0:
                self.stdout.write(f"Обработано: {i}/{total_contacts}")
            
            # Валидируем email
            validation_result = validate_email_production(contact.email)
            
            old_status = contact.status
            new_status = validation_result['status']
            
            if validation_result['is_valid']:
                if new_status == Contact.VALID:
                    stats['valid'] += 1
                elif new_status == Contact.BLACKLIST:
                    stats['blacklist'] += 1
            else:
                stats['invalid'] += 1
                new_status = Contact.INVALID
            
            # Проверяем, изменился ли статус
            if old_status != new_status:
                stats['changed'] += 1
                if not dry_run:
                    contact.status = new_status
                    contact.save(update_fields=['status'])
                self.stdout.write(
                    f"  {contact.email}: {old_status} → {new_status}"
                )
            else:
                stats['unchanged'] += 1
        
        # Выводим статистику
        self.stdout.write("\n" + "="*50)
        self.stdout.write("РЕЗУЛЬТАТЫ ВАЛИДАЦИИ:")
        self.stdout.write(f"  Всего контактов: {total_contacts}")
        self.stdout.write(f"  Действительных: {stats['valid']}")
        self.stdout.write(f"  Недействительных: {stats['invalid']}")
        self.stdout.write(f"  В черном списке: {stats['blacklist']}")
        self.stdout.write(f"  Изменено статусов: {stats['changed']}")
        self.stdout.write(f"  Без изменений: {stats['unchanged']}")
        
        if dry_run:
            self.stdout.write("\nДля применения изменений запустите команду без --dry-run")
        else:
            self.stdout.write("\nВалидация завершена!") 