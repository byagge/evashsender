from django.core.management.base import BaseCommand
from apps.mailer.models import ContactList, ImportTask, Contact
from apps.mailer.utils import parse_emails, validate_email_production
from django.utils import timezone
import time
import os


class Command(BaseCommand):
    help = 'Background import contacts for a specific task'

    def add_arguments(self, parser):
        parser.add_argument('--task-id', type=str, required=True, help='Import task ID')
        parser.add_argument('--file-path', type=str, required=True, help='Path to the uploaded file')

    def handle(self, *args, **options):
        task_id = options['task_id']
        file_path = options['file_path']

        try:
            # Получаем задачу импорта
            task = ImportTask.objects.get(id=task_id)
            
            # Проверяем, что файл существует
            if not os.path.exists(file_path):
                task.status = ImportTask.FAILED
                task.error_message = f"File not found: {file_path}"
                task.completed_at = timezone.now()
                task.save()
                self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
                return

            # Проверяем, что директория существует
            file_dir = os.path.dirname(file_path)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir, exist_ok=True)

            # Обновляем статус на "обрабатывается"
            task.status = ImportTask.PROCESSING
            task.started_at = timezone.now()
            task.save()

            # Читаем файл
            with open(file_path, 'rb') as f:
                emails = parse_emails(f, task.filename)

            task.total_emails = len(emails)
            task.save()

            # Обрабатываем email адреса
            contacts_to_create = []
            contacts_to_update = []
            processed = 0

            for email in emails:
                try:
                    processed += 1
                    
                    # Обновляем прогресс каждые 50 email
                    if processed % 50 == 0:
                        task.processed_emails = processed
                        task.save()

                    # Валидируем email
                    validation_result = validate_email_production(email)
                    
                    if validation_result['is_valid']:
                        status_code = validation_result['status']
                        
                        # Проверяем, существует ли уже контакт
                        try:
                            existing_contact = Contact.objects.get(
                                contact_list=task.contact_list,
                                email=email
                            )
                            # Обновляем статус если нужно
                            if existing_contact.status != status_code:
                                existing_contact.status = status_code
                                contacts_to_update.append(existing_contact)
                        except Contact.DoesNotExist:
                            # Создаем новый контакт
                            new_contact = Contact(
                                contact_list=task.contact_list,
                                email=email,
                                status=status_code
                            )
                            contacts_to_create.append(new_contact)
                            task.imported_count += 1
                            if status_code == Contact.BLACKLIST:
                                task.blacklisted_count += 1
                    else:
                        # Добавляем невалидные email как INVALID
                        try:
                            existing_contact = Contact.objects.get(
                                contact_list=task.contact_list,
                                email=email
                            )
                        except Contact.DoesNotExist:
                            new_contact = Contact(
                                contact_list=task.contact_list,
                                email=email,
                                status=Contact.INVALID
                            )
                            contacts_to_create.append(new_contact)
                            task.invalid_count += 1
                    
                    # Батчинг: сохраняем каждые 50 контактов
                    if len(contacts_to_create) >= 50:
                        try:
                            Contact.objects.bulk_create(contacts_to_create, ignore_conflicts=True)
                            contacts_to_create = []
                        except Exception:
                            task.error_count += len(contacts_to_create)
                            contacts_to_create = []
                    
                    # Обновляем существующие контакты
                    if len(contacts_to_update) >= 50:
                        try:
                            Contact.objects.bulk_update(contacts_to_update, ['status'])
                            contacts_to_update = []
                        except Exception:
                            task.error_count += len(contacts_to_update)
                            contacts_to_update = []
                            
                except Exception:
                    task.error_count += 1
                    continue

            # Сохраняем оставшиеся контакты
            if contacts_to_create:
                try:
                    Contact.objects.bulk_create(contacts_to_create, ignore_conflicts=True)
                except Exception:
                    task.error_count += len(contacts_to_create)

            if contacts_to_update:
                try:
                    Contact.objects.bulk_update(contacts_to_update, ['status'])
                except Exception:
                    task.error_count += len(contacts_to_update)

            # Завершаем задачу
            task.status = ImportTask.COMPLETED
            task.processed_emails = processed
            task.completed_at = timezone.now()
            task.save()

            # Удаляем временный файл
            try:
                os.remove(file_path)
            except:
                pass



        except ImportTask.DoesNotExist:
            pass
        except Exception as e:
            # Обновляем задачу с ошибкой
            try:
                task = ImportTask.objects.get(id=task_id)
                task.status = ImportTask.FAILED
                task.error_message = str(e)
                task.completed_at = timezone.now()
                task.save()
            except:
                pass 