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
            
            if settings.EMAIL_USE_TLS:
                connection.starttls()
            
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_campaign(self, campaign_id: str) -> Dict[str, Any]:
    """
    Основная задача для отправки кампании
    Разбивает кампанию на батчи и отправляет их асинхронно
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        
        # Проверяем, что кампания не уже отправляется
        if campaign.status == Campaign.STATUS_SENDING:
            print(f"Кампания {campaign_id} уже отправляется")
            return {'error': 'Campaign already sending'}
        
        # Обновляем статус кампании
        campaign.status = Campaign.STATUS_SENDING
        campaign.save(update_fields=['status'])
        
        # Получаем все контакты
        contacts = set()
        for contact_list in campaign.contact_lists.all():
            contacts.update(contact_list.contacts.all())
        
        total_contacts = len(contacts)
        contacts_list = list(contacts)
        
        if total_contacts == 0:
            campaign.status = Campaign.STATUS_FAILED
            campaign.save(update_fields=['status'])
            return {'error': 'No contacts found'}
        
        # Обновляем прогресс
        current_task.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': total_contacts,
                'status': f'Подготовка к отправке {total_contacts} писем'
            }
        )
        
        # Разбиваем на батчи
        batch_size = getattr(settings, 'EMAIL_BATCH_SIZE', 100)
        batches = [
            contacts_list[i:i + batch_size] 
            for i in range(0, len(contacts_list), batch_size)
        ]
        
        print(f"Кампания {campaign.name}: {total_contacts} писем, {len(batches)} батчей")
        
        # Создаем задачи для каждого батча
        batch_tasks = []
        for i, batch in enumerate(batches):
            task = send_email_batch.delay(
                campaign_id=campaign_id,
                contact_ids=[c.id for c in batch],
                batch_number=i + 1,
                total_batches=len(batches)
            )
            batch_tasks.append(task)
        
        # Ждем завершения всех батчей
        results = []
        for task in batch_tasks:
            try:
                result = task.get(timeout=1800)  # 30 минут timeout
                results.append(result)
            except Exception as e:
                print(f"Ошибка в батче: {e}")
                results.append({'sent': 0, 'failed': len(batch), 'error': str(e)})
        
        # Подсчитываем общую статистику
        total_sent = sum(r.get('sent', 0) for r in results)
        total_failed = sum(r.get('failed', 0) for r in results)
        
        # Обновляем статус кампании
        if total_failed == 0:
            campaign.status = Campaign.STATUS_SENT
        else:
            campaign.status = Campaign.STATUS_FAILED
        
        campaign.sent_at = timezone.now()
        campaign.celery_task_id = None  # Очищаем task_id после завершения
        campaign.save(update_fields=['status', 'sent_at', 'celery_task_id'])
        
        print(f"Кампания {campaign.name} завершена: {total_sent} отправлено, {total_failed} ошибок")
        
        return {
            'campaign_id': campaign_id,
            'total_contacts': total_contacts,
            'sent': total_sent,
            'failed': total_failed,
            'success_rate': (total_sent / total_contacts * 100) if total_contacts > 0 else 0
        }
        
    except Campaign.DoesNotExist:
        raise self.retry(countdown=60, max_retries=2)
    except Exception as exc:
        # Обновляем статус кампании на failed
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.status = Campaign.STATUS_FAILED
            campaign.celery_task_id = None  # Очищаем task_id при ошибке
            campaign.save(update_fields=['status', 'celery_task_id'])
        except:
            pass
        
        print(f"Критическая ошибка в кампании {campaign_id}: {exc}")
        raise self.retry(exc=exc, countdown=120, max_retries=3)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_email_batch(self, campaign_id: str, contact_ids: List[int], 
                    batch_number: int, total_batches: int) -> Dict[str, Any]:
    """
    Отправка батча писем с rate limiting и retry механизмом
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        contacts = Contact.objects.filter(id__in=contact_ids)
        
        # Получаем SMTP соединение из пула
        smtp_connection = smtp_pool.get_connection()
        
        sent_count = 0
        failed_count = 0
        rate_limit = getattr(settings, 'EMAIL_RATE_LIMIT', 50)
        
        for i, contact in enumerate(contacts):
            try:
                # Rate limiting
                if i > 0 and i % rate_limit == 0:
                    time.sleep(1)  # Пауза 1 секунда каждые rate_limit писем
                
                # Отправляем письмо
                result = send_single_email.delay(
                    campaign_id=campaign_id,
                    contact_id=contact.id
                )
                
                # Ждем результат с timeout
                email_result = result.get(timeout=30)
                
                if email_result.get('success'):
                    sent_count += 1
                else:
                    failed_count += 1
                
                # Обновляем прогресс
                current_task.update_state(
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
        smtp_pool.return_connection(smtp_connection)
        
        return {
            'batch_number': batch_number,
            'sent': sent_count,
            'failed': failed_count,
            'total': len(contacts)
        }
        
    except Exception as exc:
        # Возвращаем соединение в пул в случае ошибки
        try:
            smtp_pool.return_connection(smtp_connection)
        except:
            pass
        
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_single_email(self, campaign_id: str, contact_id: int) -> Dict[str, Any]:
    """
    Отправка одного письма с полным retry механизмом
    """
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        contact = Contact.objects.get(id=contact_id)
        
        # Создаем запись для отслеживания
        tracking = EmailTracking.objects.create(
            campaign=campaign,
            contact=contact,
            tracking_id=str(uuid.uuid4())
        )
        
        # Подготавливаем контент письма
        html_content = campaign.template.html_content
        if campaign.content:
            html_content = html_content.replace('{{content}}', campaign.content)
        
        # Добавляем tracking pixel
        tracking_pixel = f'<img src="/campaigns/{campaign.id}/track-open/?tracking_id={tracking.tracking_id}" width="1" height="1" />'
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', f'{tracking_pixel}</body>')
        else:
            html_content += tracking_pixel
        
        # Создаем plain text версию
        import re
        plain_text = re.sub(r'<[^>]+>', '', html_content)
        plain_text = re.sub(r'\s+', ' ', plain_text).strip()
        
        # Подготавливаем отправителя
        sender_name = campaign.sender_name
        if not sender_name:
            sender_name = campaign.sender_email.sender_name
            if not sender_name:
                email_parts = campaign.sender_email.email.split('@')
                if len(email_parts) > 0:
                    email_name = email_parts[0]
                    if email_name == 'mednews':
                        sender_name = "Медновости"
                    elif email_name == 'noreply':
                        sender_name = "VashSender"
                    else:
                        sender_name = email_name.replace('.', ' ').replace('_', ' ').title()
                else:
                    sender_name = "Отправитель"
        
        from_email = f"{sender_name} <{campaign.sender_email.email}>"
        
        # Создаем и отправляем письмо
        email = EmailMultiAlternatives(
            subject=campaign.subject,
            body=plain_text,
            from_email=from_email,
            to=[contact.email],
            reply_to=[campaign.sender_email.reply_to] if campaign.sender_email.reply_to else None
        )
        email.attach_alternative(html_content, "text/html")
        
        # Отправляем с timeout
        email.send()
        
        # Отмечаем как отправленное
        CampaignRecipient.objects.create(
            campaign=campaign,
            contact=contact,
            is_sent=True,
            sent_at=timezone.now()
        )
        
        # Отмечаем как доставленное
        tracking.mark_as_delivered()
        
        return {
            'success': True,
            'email': contact.email,
            'tracking_id': tracking.tracking_id
        }
        
    except Exception as exc:
        # Логируем ошибку
        print(f"Ошибка отправки письма {contact.email}: {str(exc)}")
        
        # Пытаемся повторить отправку
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        
        return {
            'success': False,
            'email': contact.email,
            'error': str(exc)
        }


@shared_task
def cleanup_smtp_connections():
    """Очистка SMTP соединений"""
    smtp_pool.close_all()


@shared_task
def monitor_campaign_progress():
    """Мониторинг прогресса кампаний"""
    active_campaigns = Campaign.objects.filter(status=Campaign.STATUS_SENDING)
    
    for campaign in active_campaigns:
        total_recipients = CampaignRecipient.objects.filter(campaign=campaign).count()
        sent_recipients = CampaignRecipient.objects.filter(
            campaign=campaign, 
            is_sent=True
        ).count()
        
        if total_recipients > 0:
            progress = (sent_recipients / total_recipients) * 100
            
            # Сохраняем прогресс в кэше
            cache.set(
                f'campaign_progress_{campaign.id}',
                {
                    'total': total_recipients,
                    'sent': sent_recipients,
                    'progress': progress
                },
                timeout=3600
            ) 