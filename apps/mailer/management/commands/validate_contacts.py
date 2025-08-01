from django.core.management.base import BaseCommand
from apps.mailer.models import Contact, ContactList
from apps.mailer.utils import validate_email_production

class Command(BaseCommand):
    help = 'Validate contacts in background'

    def add_arguments(self, parser):
        parser.add_argument('--list-id', type=str, help='Contact list ID to validate')
        parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
        parser.add_argument('--status', type=str, default='valid', help='Status to validate (valid, invalid, all)')

    def handle(self, *args, **options):
        list_id = options.get('list_id')
        batch_size = options.get('batch_size')
        status_filter = options.get('status')

        if list_id:
            try:
                contact_list = ContactList.objects.get(id=list_id)
                self.stdout.write(f'Validating contacts in list: {contact_list.name}')
            except ContactList.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Contact list with ID {list_id} not found'))
                return
        else:
            self.stdout.write('Validating all contacts in all lists')
            contact_list = None

        # Определяем фильтр по статусу
        if status_filter == 'valid':
            status_filter = Contact.VALID
        elif status_filter == 'invalid':
            status_filter = Contact.INVALID
        else:
            status_filter = None
        
        # Получаем контакты для валидации
        if contact_list:
            if status_filter:
                contacts = Contact.objects.filter(contact_list=contact_list, status=status_filter)
            else:
                contacts = Contact.objects.filter(contact_list=contact_list)
        else:
            if status_filter:
                contacts = Contact.objects.filter(status=status_filter)
        else:
            contacts = Contact.objects.all()
        
        total_contacts = contacts.count()
        self.stdout.write(f'Found {total_contacts} contacts to validate')
        
        if total_contacts == 0:
            self.stdout.write('No contacts to validate')
            return
        
        # Валидируем контакты батчами
        processed = 0
        updated = 0
        errors = 0

        for i in range(0, total_contacts, batch_size):
            batch = contacts[i:i + batch_size]
            
            for contact in batch:
                try:
                    processed += 1
                    
                    if processed % 100 == 0:
                        self.stdout.write(f'Processed {processed}/{total_contacts} contacts')
            
            # Валидируем email
            validation_result = validate_email_production(contact.email)
            
                    # Обновляем статус если нужно
                    if validation_result['is_valid']:
            new_status = validation_result['status']
                        if contact.status != new_status:
                    contact.status = new_status
                    contact.save(update_fields=['status'])
                            updated += 1
            else:
                        if contact.status != Contact.INVALID:
                            contact.status = Contact.INVALID
                            contact.save(update_fields=['status'])
                            updated += 1
                            
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error validating contact {contact.email}: {e}'))
                    errors += 1
                    continue

        self.stdout.write(self.style.SUCCESS(f'Validation completed!'))
        self.stdout.write(f'Total processed: {processed}')
        self.stdout.write(f'Updated: {updated}')
        self.stdout.write(f'Errors: {errors}') 