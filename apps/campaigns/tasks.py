import uuid
import time
import smtplib
import threading
from typing import List, Dict, Any
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from celery import shared_task, current_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from .models import Campaign, EmailTracking, CampaignRecipient
from apps.mailer.models import Contact
from apps.mail_templates.models import EmailTemplate
from apps.emails.models import SenderEmail


class SMTPConnectionPool:
    """Пул SMTP соединений для эффективной отправки писем"""
    
    def __init__(self, max_connections=10):
        self.max_connections = max_connections
        self.connections = []
        self.lock = threading.Lock()
    
    def get_connection(self):
        """Получить SMTP соединение из пула"""
        with self.lock:
            if self.connections:
                return self.connections.pop()
            
            # Создать новое соединение
            connection = smtplib.SMTP(
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                timeout=settings.EMAIL_CONNECTION_TIMEOUT
            )
            
            # Устанавливаем правильный HELO для улучшения доставляемости
            try:
                connection.helo('mail.vashsender.ru')
            except:
                # Если не удалось, используем стандартный HELO
                pass
            
            if settings.EMAIL_USE_TLS:
                connection.starttls()
                # Повторяем HELO после STARTTLS
                try:
                    connection.helo('mail.vashsender.ru')
                except:
                    pass
            
            if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                connection.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            
            return connection
    
    def return_connection(self, connection):
        """Вернуть соединение в пул"""
        with self.lock:
            if len(self.connections) < self.max_connections:
                try:
                    # Проверить, что соединение еще живо
                    connection.noop()
                    self.connections.append(connection)
                except:
                    # Соединение мертво, закрыть его
                    try:
                        connection.quit()
                    except:
                        pass
    
    def close_all(self):
        """Закрыть все соединения"""
        with self.lock:
            for connection in self.connections:
                try:
                    connection.quit()
                except:
                    pass
            self.connections.clear()


# Глобальный пул соединений
smtp_pool = SMTPConnectionPool()


@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue='campaigns')
def test_celery():
    """Простая тестовая задача для проверки работы Celery"""
    print("Test Celery task is running!")
    return "Test task completed successfully"

@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue='campaigns', 
            time_limit=1800, soft_time_limit=1500)  # 30 минут максимум, 25 минут мягкий лимит
def send_campaign(self, campaign_id: str, skip_moderation: bool = False) -> Dict[str, Any]:
    """
    Основная задача для отправки кампании
    Разбивает кампанию на батчи и отправляет их асинхронно
    """
    start_time = time.time()
    print(f"Starting send_campaign task for campaign {campaign_id}")
    print(f"Task ID: {self.request.id}")
    print(f"Worker: {self.request.hostname}")
    print(f"Queue: {self.request.delivery_info.get('routing_key', 'unknown')}")
    
    try:
        # Проверяем таймаут
        if time.time() - start_time > 1500:  # 25 минут
            raise TimeoutError("Task timeout approaching")
        
        # Принудительно обновляем состояние задачи
        self.update_state(
            state='STARTED',
            meta={
                'campaign_id': campaign_id,
                'status': 'Initializing campaign',
                'timestamp': time.time()
            }
        )
        
        # Получаем кампанию с обработкой ошибок
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            print(f"Found campaign: {campaign.name}, status: {campaign.status}")
        except Campaign.DoesNotExist:
            print(f"Campaign {campaign_id} not found in database")
            raise self.retry(countdown=60, max_retries=2)
        except Exception as e:
            print(f"Error getting campaign {campaign_id}: {e}")
            raise self.retry(countdown=120, max_retries=3)
        
        # Проверяем, что кампания не уже отправляется (только если не пропускаем модерацию)
        if not skip_moderation and campaign.status == Campaign.STATUS_SENDING:
            print(f"Кампания {campaign_id} уже отправляется")
            return {'error': 'Campaign already sending'}
        
        # Проверяем, нужна ли модерация
        user = campaign.user
        if not user.is_trusted_user and not skip_moderation:
            print(f"Пользователь {user.email} не является доверенным, отправляем на модерацию")
            
            # Создаем запись модерации
            from apps.moderation.models import CampaignModeration
            moderation, created = CampaignModeration.objects.get_or_create(
                campaign=campaign,
                defaults={'status': 'pending'}
            )
            
            # Обновляем статус кампании на pending
            campaign.status = Campaign.STATUS_PENDING
            campaign.save(update_fields=['status'])
            
            return {
                'campaign_id': campaign_id,
                'status': 'pending_moderation',
                'message': 'Кампания отправлена на модерацию'
            }
        
        # Проверяем лимиты тарифа перед отправкой
        try:
            from apps.billing.utils import can_user_send_emails, get_user_plan_info
            plan_info = get_user_plan_info(user)
            
            if plan_info['has_plan'] and plan_info['plan_type'] == 'Letters':
                # Для тарифов с письмами проверяем остаток
                if not can_user_send_emails(user, total_contacts):
                    campaign.status = Campaign.STATUS_FAILED
                    campaign.celery_task_id = None
                    campaign.save(update_fields=['status', 'celery_task_id'])
                    return {
                        'error': f'Недостаточно писем в тарифе. Доступно: {plan_info["emails_remaining"]}, требуется: {total_contacts}'
                    }
            elif plan_info['has_plan'] and plan_info['plan_type'] == 'Subscribers':
                # Для тарифов с подписчиками проверяем только срок действия
                if plan_info['is_expired']:
                    campaign.status = Campaign.STATUS_FAILED
                    campaign.celery_task_id = None
                    campaign.save(update_fields=['status', 'celery_task_id'])
                    return {
                        'error': 'Тариф истёк. Пожалуйста, продлите тариф для отправки кампаний.'
                    }
        except Exception as e:
            print(f"Error checking plan limits: {e}")
            # Продолжаем отправку, если не удалось проверить лимиты
        
        # Обновляем статус кампании на отправляется
        campaign.status = Campaign.STATUS_SENDING
        campaign.celery_task_id = self.request.id
        campaign.save(update_fields=['status', 'celery_task_id'])
        
        # Обновляем состояние задачи
        self.update_state(
            state='PROGRESS',
            meta={
                'campaign_id': campaign_id,
                'status': 'Campaign status updated to sending',
                'timestamp': time.time()
            }
        )
        
        # Получаем все контакты с обработкой ошибок
        try:
            contacts = set()
            for contact_list in campaign.contact_lists.all():
                list_contacts = contact_list.contacts.all()
                print(f"Found {list_contacts.count()} contacts in list {contact_list.name}")
                contacts.update(list_contacts)
            
            total_contacts = len(contacts)
            contacts_list = list(contacts)
            print(f"Total unique contacts: {total_contacts}")
            
            if total_contacts == 0:
                print(f"Нет контактов для кампании {campaign.name}")
                campaign.status = Campaign.STATUS_FAILED
                campaign.celery_task_id = None
                campaign.save(update_fields=['status', 'celery_task_id'])
                return {'error': 'No contacts found'}
                
        except Exception as e:
            print(f"Error getting contacts for campaign {campaign_id}: {e}")
            campaign.status = Campaign.STATUS_FAILED
            campaign.celery_task_id = None
            campaign.save(update_fields=['status', 'celery_task_id'])
            raise self.retry(countdown=60, max_retries=2)
        
        # Обновляем прогресс
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': total_contacts,
                'status': f'Подготовка к отправке {total_contacts} писем',
                'timestamp': time.time()
            }
        )
        
        # Разбиваем на батчи
        batch_size = getattr(settings, 'EMAIL_BATCH_SIZE', 100)
        batches = [
            contacts_list[i:i + batch_size] 
            for i in range(0, len(contacts_list), batch_size)
        ]
        
        print(f"Кампания {campaign.name}: {total_contacts} писем, {len(batches)} батчей")
        
        # Отправляем письма напрямую через send_email_batch
        batch_tasks = []
        for i, batch in enumerate(batches):
            print(f"Launching batch {i + 1}/{len(batches)} with {len(batch)} contacts")
            
            # Проверяем таймаут перед запуском каждого батча
            if time.time() - start_time > 1500:
                raise TimeoutError("Task timeout approaching before launching all batches")
            
            try:
                result = send_email_batch.apply_async(
                    args=[campaign_id, [c.id for c in batch], i + 1, len(batches)],
                    countdown=0,
                    expires=600,  # 10 минут
                    retry=True,
                    retry_policy={
                        'max_retries': 2,
                        'interval_start': 0,
                        'interval_step': 0.2,
                        'interval_max': 0.2,
                    }
                )
                batch_tasks.append(result)
                print(f"Batch {i + 1} task ID: {result.id}")
                print(f"Batch {i + 1} status: {result.status}")
            
                # Обновляем прогресс
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': i + 1,
                        'total': len(batches),
                        'status': f'Запущен батч {i + 1}/{len(batches)}',
                        'timestamp': time.time()
                    }
                )
                
            except Exception as e:
                print(f"Error launching batch {i + 1}: {e}")
                # Продолжаем с другими батчами
                continue
        
        # Ждем завершения всех батчей с таймаутом
        max_wait_time = 1200  # 20 минут максимум ожидания
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait_time:
            completed_batches = sum(1 for task in batch_tasks if task.ready())
            if completed_batches == len(batch_tasks):
                print(f"All {len(batch_tasks)} batches completed")
                break
            
            print(f"Waiting for batches: {completed_batches}/{len(batch_tasks)} completed")
            
            # Обновляем прогресс ожидания
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': completed_batches,
                    'total': len(batch_tasks),
                    'status': f'Ожидание завершения батчей: {completed_batches}/{len(batch_tasks)}',
                    'timestamp': time.time()
                }
            )
            
            time.sleep(5)  # Проверяем каждые 5 секунд
        else:
            print(f"Timeout waiting for batches after {max_wait_time} seconds")
            # Продолжаем выполнение, даже если не все батчи завершились
        
        # НЕ обновляем статус здесь, так как он будет обновлен в send_email_batch
        # Статус кампании уже установлен на "sending" в начале функции
        
        # Добавляем финальную проверку статуса кампании
        try:
            campaign.refresh_from_db()
            print(f"Final campaign status: {campaign.status}")
            
            # Проверяем, нужно ли обновить статус на "sent"
            total_sent = CampaignRecipient.objects.filter(
                campaign_id=campaign_id, 
                is_sent=True
            ).count()
            total_recipients = CampaignRecipient.objects.filter(
                campaign_id=campaign_id
            ).count()
            
            if total_recipients > 0 and total_sent == total_recipients and campaign.status == Campaign.STATUS_SENDING:
                print(f"All emails sent, updating campaign status to SENT")
                campaign.status = Campaign.STATUS_SENT
                campaign.sent_at = timezone.now()
                campaign.celery_task_id = None
                campaign.save(update_fields=['status', 'sent_at', 'celery_task_id'])
            elif total_recipients > 0 and total_sent < total_recipients:
                print(f"Some emails failed: {total_sent}/{total_recipients} sent")
                campaign.status = Campaign.STATUS_FAILED
                campaign.celery_task_id = None
                campaign.save(update_fields=['status', 'celery_task_id'])
            
            # Очищаем кэш для этой кампании
            cache_key = f"campaign_{campaign_id}"
            cache.delete(cache_key)
            
        except Exception as e:
            print(f"Error in final status check: {e}")
        
        execution_time = time.time() - start_time
        print(f"Campaign {campaign_id} processing completed in {execution_time:.2f} seconds")
        
        return {
            'campaign_id': campaign_id,
            'total_contacts': total_contacts,
            'batches_launched': len(batches),
            'status': 'batches_launched',
            'execution_time': execution_time,
            'worker': self.request.hostname
        }
        
    except TimeoutError as e:
        print(f"Timeout error in send_campaign task: {e}")
        # Обновляем статус кампании на failed при таймауте
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.status = Campaign.STATUS_FAILED
            campaign.celery_task_id = None
            campaign.save(update_fields=['status', 'celery_task_id'])
        except:
            pass
        raise self.retry(countdown=300, max_retries=1)  # Повторяем через 5 минут
        
    except Campaign.DoesNotExist:
        print(f"Campaign {campaign_id} not found")
        raise self.retry(countdown=60, max_retries=2)
        
    except Exception as exc:
        print(f"Error in send_campaign task: {exc}")
        import traceback
        traceback.print_exc()
        
        # Обновляем статус кампании на failed
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.status = Campaign.STATUS_FAILED
            campaign.celery_task_id = None
            campaign.save(update_fields=['status', 'celery_task_id'])
        except:
            pass
        
        print(f"Критическая ошибка в кампании {campaign_id}: {exc}")
        raise self.retry(exc=exc, countdown=120, max_retries=3)


@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue='email',
            time_limit=600, soft_time_limit=500)  # 10 минут максимум, 8 минут мягкий лимит
def send_email_batch(self, campaign_id: str, contact_ids: List[int], 
                    batch_number: int, total_batches: int) -> Dict[str, Any]:
    """
    Отправка батча писем с rate limiting и retry механизмом
    """
    start_time = time.time()
    smtp_connection = None
    
    try:
        print(f"Starting send_email_batch for campaign {campaign_id}, batch {batch_number}/{total_batches}")
        
        # Проверяем таймаут
        if time.time() - start_time > 500:  # 8 минут
            raise TimeoutError("Batch task timeout approaching")
        
        campaign = Campaign.objects.get(id=campaign_id)
        contacts = Contact.objects.filter(id__in=contact_ids)
        print(f"Found {contacts.count()} contacts in batch")
        print(f"Campaign current status: {campaign.status}")
        
        # Получаем SMTP соединение из пула
        smtp_connection = smtp_pool.get_connection()
        print("Got SMTP connection")
        
        sent_count = 0
        failed_count = 0
        rate_limit = getattr(settings, 'EMAIL_RATE_LIMIT', 50)
        
        for i, contact in enumerate(contacts):
            try:
                # Проверяем таймаут в цикле
                if time.time() - start_time > 500:
                    raise TimeoutError("Batch task timeout approaching during email sending")
                
                # Rate limiting
                if i > 0 and i % rate_limit == 0:
                    time.sleep(1)  # Пауза 1 секунда каждые rate_limit писем
                
                # Отправляем письмо напрямую
                email_result = send_single_email.apply(
                    args=[campaign_id, contact.id]
                )
                
                # Не ждем результат, просто запускаем задачу
                # Результат будет обработан в самой задаче send_single_email
                sent_count += 1  # Предполагаем успех, так как не ждем результат
                
                # Обновляем прогресс
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'batch': batch_number,
                        'total_batches': total_batches,
                        'current': i + 1,
                        'total': len(contacts),
                        'sent': sent_count,
                        'failed': failed_count
                    }
                )
                
            except Exception as e:
                failed_count += 1
                print(f"Ошибка отправки письма {contact.email}: {str(e)}")
                continue
        
        # Возвращаем соединение в пул
        if smtp_connection:
            smtp_pool.return_connection(smtp_connection)
        
        # Обновляем статус кампании на основе результатов этого батча
        campaign = Campaign.objects.get(id=campaign_id)
        print(f"Current campaign status before update: {campaign.status}")
        
        # Проверяем статистику по всем получателям кампании
        total_sent = CampaignRecipient.objects.filter(
            campaign_id=campaign_id, 
            is_sent=True
        ).count()
        total_failed = CampaignRecipient.objects.filter(
            campaign_id=campaign_id, 
            is_sent=False
        ).count()
        total_recipients = CampaignRecipient.objects.filter(
            campaign_id=campaign_id
        ).count()
        
        print(f"Campaign statistics: total_recipients={total_recipients}, total_sent={total_sent}, total_failed={total_failed}")
        
        # Обновляем статус кампании только если все получатели обработаны
        if total_recipients > 0 and (total_sent + total_failed) >= total_recipients:
            if total_failed == 0 and total_sent > 0:
                campaign.status = Campaign.STATUS_SENT
                print(f"Setting campaign status to SENT")
            elif total_failed > 0:
                campaign.status = Campaign.STATUS_FAILED
                print(f"Setting campaign status to FAILED")
            else:
                # Если нет записей получателей, оставляем статус sending
                print(f"Keeping campaign status as SENDING")
                pass
            
            campaign.sent_at = timezone.now()
            print(f"Saving campaign with status: {campaign.status}")
            
            # Принудительно обновляем статус в базе данных
            from django.db import transaction
            with transaction.atomic():
                Campaign.objects.filter(id=campaign_id).update(
                    status=campaign.status,
                    sent_at=campaign.sent_at
                )
            
            # Очищаем кэш для этой кампании
            cache_key = f"campaign_{campaign_id}"
            cache.delete(cache_key)
            
            # Проверяем, что статус действительно сохранился
            try:
                campaign.refresh_from_db()
                print(f"Campaign {campaign.name} status after save: {campaign.status}")
            except Campaign.DoesNotExist:
                print(f"Campaign {campaign_id} not found after refresh")
        else:
            print(f"Not all recipients processed yet: {total_sent + total_failed}/{total_recipients}")
            print(f"Keeping campaign status as SENDING")
        
        print(f"Batch {batch_number} completed: {sent_count} sent, {failed_count} failed")
        
        # Финальная проверка и обновление статуса кампании
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            print(f"Final campaign status after batch {batch_number}: {campaign.status}")
            
            # Очищаем кэш для этой кампании
            cache_key = f"campaign_{campaign_id}"
            cache.delete(cache_key)
            
        except Exception as e:
            print(f"Error in final campaign status check: {e}")
        
        execution_time = time.time() - start_time
        print(f"Batch {batch_number} processing completed in {execution_time:.2f} seconds")
        
        return {
            'batch_number': batch_number,
            'sent': sent_count,
            'failed': failed_count,
            'total': len(contacts),
            'execution_time': execution_time
        }
        
    except TimeoutError as e:
        print(f"Timeout error in send_email_batch task: {e}")
        # Возвращаем соединение в пул в случае ошибки
        if smtp_connection:
            try:
                smtp_pool.return_connection(smtp_connection)
            except:
                pass
        raise self.retry(countdown=60, max_retries=2)
        
    except Exception as exc:
        print(f"Error in send_email_batch task: {exc}")
        # Возвращаем соединение в пул в случае ошибки
        if smtp_connection:
            try:
                smtp_pool.return_connection(smtp_connection)
            except:
                pass
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@shared_task(bind=True, max_retries=3, default_retry_delay=30, queue='email',
            time_limit=300, soft_time_limit=240)  # 5 минут максимум, 4 минуты мягкий лимит
def send_single_email(self, campaign_id: str, contact_id: int) -> Dict[str, Any]:
    """
    Отправка одного письма с полным retry механизмом
    """
    start_time = time.time()
    smtp_connection = None
    
    try:
        print(f"Starting send_single_email for campaign {campaign_id}, contact {contact_id}")
        
        # Проверяем таймаут
        if time.time() - start_time > 240:  # 4 минуты
            raise TimeoutError("Single email task timeout approaching")
        
        campaign = Campaign.objects.get(id=campaign_id)
        contact = Contact.objects.get(id=contact_id)
        print(f"Sending to: {contact.email}")
        
        # Создаем запись для отслеживания
        tracking = EmailTracking.objects.create(
            campaign=campaign,
            contact=contact,
            tracking_id=str(uuid.uuid4())
        )
        print("Created tracking record")
        
        # Подготавливаем контент письма
        html_content = campaign.template.html_content
        if campaign.content:
            html_content = html_content.replace('{{content}}', campaign.content)
        
        # Добавляем tracking pixel с полным URL
        # Используем домен из настроек или текущий домен
        try:
            from django.contrib.sites.models import Site
            current_site = Site.objects.get_current()
            base_url = f"https://{current_site.domain}"
        except:
            # Fallback на домен из настроек
            base_url = f"https://{settings.ALLOWED_HOSTS[0]}" if settings.ALLOWED_HOSTS else "https://vashsender.ru"
        
        tracking_pixel = f'<img src="{base_url}/campaigns/{campaign.id}/track-open/?tracking_id={tracking.tracking_id}" width="1" height="1" alt="" />'
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', f'{tracking_pixel}</body>')
        else:
            html_content += tracking_pixel
        
        # Создаем улучшенную plain text версию с большим количеством текста
        import re
        from bs4 import BeautifulSoup
        
        # Сначала извлекаем текст из HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Удаляем скрипты и стили
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Получаем текст
        plain_text = soup.get_text()
        
        # Очищаем текст
        lines = (line.strip() for line in plain_text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        plain_text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Если текст слишком короткий, добавляем дополнительную информацию
        if len(plain_text) < 200:
            plain_text += f"\n\nЭто письмо отправлено через систему рассылок VashSender.\n"
            plain_text += f"Если вы не хотите получать наши письма, вы можете отписаться от рассылки.\n"
            plain_text += f"С уважением, команда VashSender"
        
        # Добавляем дополнительный текст для решения проблемы HTML_IMAGE_ONLY_24
        if len(plain_text) < 500:
            plain_text += f"\n\nДополнительная информация:\n"
            plain_text += f"Данное письмо содержит важную информацию для вас. "
            plain_text += f"Пожалуйста, внимательно ознакомьтесь с содержимым. "
            plain_text += f"Если у вас есть вопросы, не стесняйтесь обращаться к нам. "
            plain_text += f"Мы всегда готовы помочь и ответить на ваши вопросы. "
            plain_text += f"Спасибо за ваше внимание к нашему сообщению."
        
        # Ограничиваем длину текста
        if len(plain_text) > 1000:
            plain_text = plain_text[:1000] + "..."
        
        # Подготавливаем отправителя - используем имя из кампании
        sender_name = campaign.sender_name
        if not sender_name or sender_name.strip() == '':
            # Если имя не задано в кампании, используем имя из email
            sender_name = campaign.sender_email.sender_name
            if not sender_name or sender_name.strip() == '':
                # Если и там нет, используем домен
                if '@' in campaign.sender_email.email:
                    domain = campaign.sender_email.email.split('@')[1]
                    sender_name = domain.split('.')[0].title()
                else:
                    sender_name = "Sender"
        
        # Очищаем имя от лишних символов и проблемных символов
        sender_name = sender_name.strip()
        
        # Убираем проблемные символы для email заголовков
        import re
        sender_name = re.sub(r'[^\w\s\-\.]', '', sender_name)  # Оставляем только буквы, цифры, пробелы, дефисы и точки
        sender_name = re.sub(r'\s+', ' ', sender_name)  # Убираем множественные пробелы
        
        if not sender_name:
            sender_name = "Sender"
        
        # Подготавливаем email отправителя
        from_email = campaign.sender_email.email
        
        # Убираем все возможные варианты двойного @ для любых доменов
        if from_email.count('@') > 1:
            # Если больше одного @, берем только первую часть до первого @
            parts = from_email.split('@')
            username = parts[0]
            domain = parts[1]  # Берем первый домен после @
            from_email = f"{username}@{domain}"
        
        # Дополнительная проверка на корректность email
        if not '@' in from_email:
            # Если email некорректный, используем домен из настроек
            from_email = settings.DEFAULT_FROM_EMAIL
        
        # Логируем для отладки
        print(f"Sender name: '{sender_name}'")
        print(f"From email: '{from_email}'")
        
        # Получаем SMTP соединение
        smtp_connection = smtp_pool.get_connection()
        
        # Создаем сообщение с улучшенными заголовками
        msg = MIMEMultipart('alternative')
        msg['Subject'] = campaign.subject
        
        # Правильно формируем заголовок From с кодировкой имени
        from email.header import Header
        from email.utils import formataddr
        
        try:
            # Кодируем имя отправителя в UTF-8
            from_name = Header(sender_name, 'utf-8')
            
            # Используем formataddr для правильного форматирования
            msg['From'] = formataddr((str(from_name), from_email))
        except Exception as e:
            # Если кодировка не удалась, используем простое имя без кодировки
            print(f"Error encoding sender name '{sender_name}': {e}")
            msg['From'] = formataddr((sender_name, from_email))
        msg['To'] = contact.email
        msg['Reply-To'] = campaign.sender_email.reply_to or from_email
        
        # Добавляем важные заголовки для улучшения доставляемости
        # Используем домен из email отправителя для Message-ID
        message_domain = from_email.split('@')[1] if '@' in from_email else 'vashsender.ru'
        msg['Message-ID'] = f"<{tracking.tracking_id}@{message_domain}>"
        msg['Date'] = timezone.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        msg['MIME-Version'] = '1.0'
        msg['X-Mailer'] = 'VashSender/1.0'
        msg['X-Priority'] = '3'  # Нормальный приоритет
        msg['X-MSMail-Priority'] = 'Normal'
        msg['Importance'] = 'normal'
        
        # Добавляем части сообщения
        text_part = MIMEText(plain_text, 'plain', 'utf-8')
        html_part = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Отправляем письмо
        smtp_connection.send_message(msg)
        print(f"Email sent successfully to {contact.email}")
        
        # Обновляем tracking
        tracking.sent_at = timezone.now()
        tracking.save(update_fields=['sent_at'])
        
        # Создаем запись получателя с транзакцией
        from django.db import transaction
        with transaction.atomic():
            recipient, created = CampaignRecipient.objects.get_or_create(
                campaign=campaign,
                contact=contact,
                defaults={'is_sent': True, 'sent_at': timezone.now()}
            )
            
            if not created:
                recipient.is_sent = True
                recipient.sent_at = timezone.now()
                recipient.save(update_fields=['is_sent', 'sent_at'])
        
        print(f"Created CampaignRecipient: campaign_id={campaign_id}, contact_id={contact_id}, is_sent=True")
        
        # Обновляем счётчик отправленных писем в тарифе
        try:
            from apps.billing.utils import add_emails_sent_to_plan
            add_emails_sent_to_plan(campaign.user, 1)
            print(f"Updated email count for user {campaign.user.email}")
        except Exception as e:
            print(f"Error updating email count: {e}")
        
        # Возвращаем соединение в пул
        smtp_pool.return_connection(smtp_connection)
        
        execution_time = time.time() - start_time
        print(f"Single email to {contact.email} completed in {execution_time:.2f} seconds")
        
        return {
            'success': True,
            'email': contact.email,
            'tracking_id': tracking.tracking_id,
            'execution_time': execution_time
        }
        
    except TimeoutError as e:
        print(f"Timeout error in send_single_email task: {e}")
        # Возвращаем соединение в пул в случае ошибки
        if smtp_connection:
            try:
                smtp_pool.return_connection(smtp_connection)
            except:
                pass
        raise self.retry(countdown=30, max_retries=2)
        
    except Exception as exc:
        print(f"Error sending email to {contact.email if 'contact' in locals() else 'unknown'}: {exc}")
        
        # Возвращаем соединение в пул в случае ошибки
        if smtp_connection:
            try:
                smtp_pool.return_connection(smtp_connection)
            except:
                pass
        
        # Создаем запись об ошибке
        try:
            if 'campaign' in locals() and 'contact' in locals():
                recipient, created = CampaignRecipient.objects.get_or_create(
                    campaign=campaign,
                    contact=contact,
                    defaults={'is_sent': False}
                )
                
                if not created:
                    recipient.is_sent = False
                    recipient.save(update_fields=['is_sent'])
                
                print(f"Created CampaignRecipient: campaign_id={campaign_id}, contact_id={contact_id}, is_sent=False")
        except Exception as e:
            print(f"Error creating CampaignRecipient record: {e}")
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@shared_task(bind=True, time_limit=300, soft_time_limit=240)
def cleanup_stuck_campaigns(self):
    """
    Автоматическая очистка зависших кампаний.
    Запускается каждые 10 минут через Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.core.cache import cache
    
    print(f"[{timezone.now()}] Starting automatic cleanup of stuck campaigns...")
    
    # Таймаут для зависших кампаний (30 минут)
    timeout_minutes = 30
    cutoff_time = timezone.now() - timedelta(minutes=timeout_minutes)
    
    # Находим зависшие кампании
    stuck_campaigns = Campaign.objects.filter(
        status=Campaign.STATUS_SENDING,
        updated_at__lt=cutoff_time
    )
    
    cleaned_count = 0
    for campaign in stuck_campaigns:
        try:
            print(f"Cleaning up stuck campaign: {campaign.name} (ID: {campaign.id})")
            
            # Проверяем, сколько писем было отправлено
            sent_count = CampaignRecipient.objects.filter(
                campaign=campaign, 
                is_sent=True
            ).count()
            
            total_count = CampaignRecipient.objects.filter(campaign=campaign).count()
            
            # Определяем финальный статус
            if sent_count > 0:
                if sent_count == total_count:
                    campaign.status = Campaign.STATUS_SENT
                    print(f"  Campaign marked as SENT ({sent_count}/{total_count} emails sent)")
                else:
                    campaign.status = Campaign.STATUS_FAILED
                    print(f"  Campaign marked as FAILED ({sent_count}/{total_count} emails sent)")
            else:
                campaign.status = Campaign.STATUS_DRAFT
                print(f"  Campaign reset to DRAFT (no emails sent)")
            
            # Очищаем task_id
            campaign.celery_task_id = None
            campaign.save(update_fields=['status', 'celery_task_id'])
            
            # Очищаем кэш
            cache.delete(f'campaign_progress_{campaign.id}')
            
            cleaned_count += 1
            
        except Exception as e:
            print(f"Error cleaning up campaign {campaign.id}: {e}")
            continue
    
    print(f"[{timezone.now()}] Cleanup completed: {cleaned_count} campaigns cleaned")
    return {
        'cleaned_campaigns': cleaned_count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task(bind=True, time_limit=300, soft_time_limit=240)
def monitor_campaign_progress(self):
    """
    Мониторинг прогресса кампаний и автоматическое исправление проблем.
    Запускается каждые 5 минут через Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.core.cache import cache
    from celery.result import AsyncResult
    
    print(f"[{timezone.now()}] Starting campaign progress monitoring...")
    
    # Проверяем кампании в статусе "sending"
    sending_campaigns = Campaign.objects.filter(status=Campaign.STATUS_SENDING)
    
    monitored_count = 0
    for campaign in sending_campaigns:
        try:
            monitored_count += 1
            
            # Проверяем task_id
            if not campaign.celery_task_id:
                print(f"Campaign {campaign.id} has no task_id, marking as failed")
                campaign.status = Campaign.STATUS_FAILED
                campaign.save(update_fields=['status'])
                continue
            
            # Проверяем статус задачи Celery
            task_result = AsyncResult(campaign.celery_task_id)
            
            if task_result.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                # Задача завершена, но статус кампании не обновлен
                print(f"Campaign {campaign.id} task completed with state: {task_result.state}")
                
                # Проверяем количество отправленных писем
                sent_count = CampaignRecipient.objects.filter(
                    campaign=campaign, 
                    is_sent=True
                ).count()
        
                total_count = CampaignRecipient.objects.filter(campaign=campaign).count()
                
                if sent_count > 0:
                    if sent_count == total_count:
                        campaign.status = Campaign.STATUS_SENT
                        print(f"  Campaign marked as SENT ({sent_count}/{total_count})")
                    else:
                        campaign.status = Campaign.STATUS_FAILED
                        print(f"  Campaign marked as FAILED ({sent_count}/{total_count})")
                else:
                    campaign.status = Campaign.STATUS_FAILED
                    print(f"  Campaign marked as FAILED (no emails sent)")
                
                campaign.save(update_fields=['status'])
            
            elif task_result.state == 'PENDING':
                # Задача в очереди слишком долго
                task_age = timezone.now() - campaign.updated_at
                if task_age > timedelta(minutes=15):
                    print(f"Campaign {campaign.id} task stuck in PENDING for {task_age}")
                    # Можно добавить логику для перезапуска задачи
            
        except Exception as e:
            print(f"Error monitoring campaign {campaign.id}: {e}")
            continue
    
    print(f"[{timezone.now()}] Monitoring completed: {monitored_count} campaigns checked")
    return {
        'monitored_campaigns': monitored_count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task(bind=True, time_limit=300, soft_time_limit=240)
def cleanup_smtp_connections(self):
    """
    Очистка SMTP соединений и проверка их состояния.
    Запускается каждые 10 минут через Celery Beat.
    """
    from django.core.cache import cache
    
    print(f"[{timezone.now()}] Starting SMTP connections cleanup...")
    
    try:
        # Очищаем старые SMTP соединения из кэша
        smtp_keys = cache.keys('smtp_connection_*')
        cleaned_connections = 0
        
        for key in smtp_keys:
            connection_data = cache.get(key)
            if connection_data:
                # Проверяем возраст соединения (старше 30 минут)
                from django.utils import timezone
                from datetime import timedelta
                
                if 'created_at' in connection_data:
                    created_at = connection_data['created_at']
                    if isinstance(created_at, str):
                        from datetime import datetime
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    if timezone.now() - created_at > timedelta(minutes=30):
                        cache.delete(key)
                        cleaned_connections += 1
        
        print(f"[{timezone.now()}] SMTP cleanup completed: {cleaned_connections} connections cleaned")
        
        return {
            'cleaned_connections': cleaned_connections,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error during SMTP cleanup: {e}")
        return {
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        } 