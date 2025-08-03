# apps/campaigns/views.py

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET
from django.http import Http404
import uuid

from .models import Campaign, CampaignStats, EmailTracking, CampaignRecipient
from .serializers import CampaignSerializer, EmailTrackingSerializer
from apps.billing.models import Plan
from apps.campaigns.tasks import send_campaign
from django.conf import settings


class CampaignViewSet(viewsets.ModelViewSet):
    """
    REST API: CRUD кампаний + экшен send.
    """
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Campaign.objects.none()
        return Campaign.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        # Принудительно обновляем данные из базы, игнорируя кэш
        queryset = self.get_queryset()
        # Очищаем кэш для списка кампаний пользователя
        cache_key = f"campaigns_list_{request.user.id}"
        from django.core.cache import cache
        cache.delete(cache_key)
        
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        # Принудительно обновляем данные из базы, игнорируя кэш
        instance = self.get_object()
        # Очищаем кэш для конкретной кампании
        cache_key = f"campaign_{instance.id}"
        from django.core.cache import cache
        cache.delete(cache_key)
        
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        print(f"Update request data: {request.data}")
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"Serializer validated data: {serializer.validated_data}")
        
        # Если это черновик, сохраняем все поля как есть
        if instance.status == Campaign.STATUS_DRAFT:
            self.perform_update(serializer)
            print(f"Campaign after update: template={instance.template}, sender_email={instance.sender_email}, contact_lists={list(instance.contact_lists.all())}")
            return Response(serializer.data)
            
        # Для других статусов выполняем полную валидацию
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        campaign = self.get_object()
        
        print(f"Send campaign: {campaign.id}")
        print(f"Campaign status: {campaign.status}")
        print(f"Campaign template: {campaign.template}")
        print(f"Campaign sender_email: {campaign.sender_email}")
        print(f"Campaign contact_lists: {list(campaign.contact_lists.all())}")
        print(f"Campaign sender_name: {campaign.sender_name}")

        if campaign.status != Campaign.STATUS_DRAFT:
            return Response({'detail': 'Можно отправить только черновик.'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, не запущена ли уже кампания
        if campaign.celery_task_id:
            # Проверяем статус существующей задачи
            from celery.result import AsyncResult
            task_result = AsyncResult(campaign.celery_task_id)
            
            if task_result.state in ['PENDING', 'STARTED']:
                return Response({
                    'detail': 'Кампания уже отправляется.',
                    'task_id': campaign.celery_task_id,
                    'task_status': task_result.state
                }, status=status.HTTP_400_BAD_REQUEST)
            elif task_result.state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                # Очищаем старый task_id
                campaign.celery_task_id = None
                campaign.save(update_fields=['celery_task_id'])

        # --- ОГРАНИЧЕНИЕ ПО ТАРИФУ НА ОТПРАВКУ ---
        user = request.user
        plan = getattr(user, 'current_plan', None)
        if not plan:
            return Response({'error': 'Не найден тариф пользователя.'}, status=status.HTTP_400_BAD_REQUEST)
        daily_limit = getattr(plan, 'max_emails_per_day', 0)
        monthly_limit = getattr(plan, 'emails_per_month', 0)
        # Считаем сколько писем пользователь уже отправил сегодня и за месяц
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        sent_today = CampaignRecipient.objects.filter(
            campaign__user=user,
            sent_at__gte=start_of_day
        ).count()
        sent_this_month = CampaignRecipient.objects.filter(
            campaign__user=user,
            sent_at__gte=start_of_month
        ).count()
        # Сколько писем будет отправлено в этой кампании
        recipients_count = sum(cl.contacts.count() for cl in campaign.contact_lists.all())
        # Проверяем лимиты
        if daily_limit and sent_today + recipients_count > daily_limit:
            return Response({'error': f'Превышен дневной лимит отправки писем по вашему тарифу: {daily_limit}.'}, status=status.HTTP_400_BAD_REQUEST)
        if monthly_limit and sent_this_month + recipients_count > monthly_limit:
            return Response({'error': f'Превышен месячный лимит отправки писем по вашему тарифу: {monthly_limit}.'}, status=status.HTTP_400_BAD_REQUEST)

        # --- ВАЛИДАЦИЯ ПОЛЕЙ КАМПАНИИ ---
        print("Validating campaign fields:")
        print(f"  name: {campaign.name}")
        print(f"  template: {campaign.template}")
        print(f"  sender_email: {campaign.sender_email}")
        print(f"  subject: {campaign.subject}")

        # Проверяем обязательные поля
        if not campaign.name:
            return Response({'error': 'Название кампании обязательно.'}, status=status.HTTP_400_BAD_REQUEST)
        if not campaign.template:
            return Response({'error': 'Шаблон письма обязателен.'}, status=status.HTTP_400_BAD_REQUEST)
        if not campaign.sender_email:
            return Response({'error': 'Email отправителя обязателен.'}, status=status.HTTP_400_BAD_REQUEST)
        if not campaign.subject:
            return Response({'error': 'Тема письма обязательна.'}, status=status.HTTP_400_BAD_REQUEST)
        if not campaign.contact_lists.exists():
            return Response({'error': 'Список контактов обязателен.'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, что email отправителя верифицирован
        if not campaign.sender_email.is_verified:
            return Response({'error': 'Email отправителя должен быть верифицирован.'}, status=status.HTTP_400_BAD_REQUEST)

        print("Starting campaign sending...")
        
        try:
            # Проверяем доступность Celery
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            
            if not stats:
                return Response({
                    'error': 'Celery worker недоступен. Проверьте, что Celery запущен.',
                    'detail': 'No active workers found'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            print(f"Found {len(stats)} active Celery workers")
            
            # Запускаем задачу Celery с дополнительными параметрами
            print("Starting Celery task...")
            task = send_campaign.apply_async(
                args=[campaign.id],
                countdown=1,  # Запуск через 1 секунду
                expires=1800,  # Истекает через 30 минут
                retry=True,
                retry_policy={
                    'max_retries': 3,
                    'interval_start': 0,
                    'interval_step': 0.2,
                    'interval_max': 0.2,
                }
            )
            print(f"Celery task started: {task.id}")
            
            # Ждем немного и проверяем, что задача действительно запустилась
            import time
            time.sleep(2)
            
            # Проверяем статус задачи
            task_result = task.result
            print(f"Task status after 2 seconds: {task.status}")
            
            if task.status == 'PENDING':
                print("Task is still pending - this might indicate a problem")
                # Проверяем, есть ли активные задачи
                active_tasks = inspect.active()
                if active_tasks:
                    print(f"Active tasks: {active_tasks}")
                else:
                    print("No active tasks found")
            
            # Сохраняем task_id в кампании
            campaign.celery_task_id = task.id
            campaign.save(update_fields=['celery_task_id'])
            
            print(f"Task status: {task.status}")
            
            return Response({
                'message': 'Кампания запущена на отправку.',
                'task_id': task.id,
                'task_status': task.status,
                'recipients_count': recipients_count,
                'workers_count': len(stats)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error starting campaign: {e}")
            import traceback
            traceback.print_exc()
            
            # Очищаем task_id в случае ошибки
            campaign.celery_task_id = None
            campaign.save(update_fields=['celery_task_id'])
            
            return Response({
                'error': 'Ошибка запуска кампании.',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Получить прогресс отправки кампании"""
        campaign = self.get_object()
        
        from django.core.cache import cache
        
        # Получаем прогресс из кэша
        progress_data = cache.get(f'campaign_progress_{campaign.id}')
        
        if not progress_data:
            # Если нет в кэше, считаем из базы
            total_recipients = CampaignRecipient.objects.filter(campaign=campaign).count()
            sent_recipients = CampaignRecipient.objects.filter(
                campaign=campaign, 
                is_sent=True
            ).count()
            
            progress_data = {
                'total': total_recipients,
                'sent': sent_recipients,
                'progress': (sent_recipients / total_recipients * 100) if total_recipients > 0 else 0
            }
        
        return Response({
            'campaign_id': str(campaign.id),
            'status': campaign.status,
            'progress': progress_data
        })

    @action(detail=True, methods=['post'])
    def track_open(self, request, pk=None):
        """Отслеживание открытия письма"""
        tracking_id = request.GET.get('tracking_id')
        if not tracking_id:
            return Response({'error': 'Tracking ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tracking = EmailTracking.objects.get(
                campaign_id=pk,
                tracking_id=tracking_id
            )
            tracking.mark_as_opened(
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            return Response({'status': 'success'})
        except EmailTracking.DoesNotExist:
            return Response({'error': 'Invalid tracking ID'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def track_click(self, request, pk=None):
        """Отслеживание клика по ссылке"""
        tracking_id = request.GET.get('tracking_id')
        if not tracking_id:
            return Response({'error': 'Tracking ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tracking = EmailTracking.objects.get(
                campaign_id=pk,
                tracking_id=tracking_id
            )
            tracking.mark_as_clicked(
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            return Response({'status': 'success'})
        except EmailTracking.DoesNotExist:
            return Response({'error': 'Invalid tracking ID'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def track_bounce(self, request, pk=None):
        """Отслеживание отказа письма"""
        tracking_id = request.GET.get('tracking_id')
        reason = request.data.get('reason', '')
        
        if not tracking_id:
            return Response({'error': 'Tracking ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tracking = EmailTracking.objects.get(
                campaign_id=pk,
                tracking_id=tracking_id
            )
            tracking.mark_as_bounced(reason=reason)
            return Response({'status': 'success'})
        except EmailTracking.DoesNotExist:
            return Response({'error': 'Invalid tracking ID'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Получение статистики по кампаниям"""
        # Получаем все кампании пользователя
        campaigns = self.get_queryset()
        
        # Считаем общую статистику
        total_sent = sum(c.emails_sent for c in campaigns)
        total_delivered = sum(c.delivered_emails for c in campaigns)
        total_opened = sum(c.emails_sent * (c.open_rate / 100) for c in campaigns)
        total_clicked = sum(c.emails_sent * (c.click_rate / 100) for c in campaigns)
        
        # Считаем статистику за последние 7 дней для тренда
        week_ago = timezone.now() - timezone.timedelta(days=7)
        week_campaigns = campaigns.filter(created_at__gte=week_ago)
        
        week_sent = sum(c.emails_sent for c in week_campaigns)
        week_delivered = sum(c.delivered_emails for c in week_campaigns)
        week_opened = sum(c.emails_sent * (c.open_rate / 100) for c in week_campaigns)
        week_clicked = sum(c.emails_sent * (c.click_rate / 100) for c in week_campaigns)
        
        # Считаем тренды (процент изменения)
        prev_week = week_ago - timezone.timedelta(days=7)
        prev_week_campaigns = campaigns.filter(
            created_at__gte=prev_week,
            created_at__lt=week_ago
        )
        
        prev_week_sent = sum(c.emails_sent for c in prev_week_campaigns)
        prev_week_delivered = sum(c.delivered_emails for c in prev_week_campaigns)
        prev_week_opened = sum(c.emails_sent * (c.open_rate / 100) for c in prev_week_campaigns)
        prev_week_clicked = sum(c.emails_sent * (c.click_rate / 100) for c in prev_week_campaigns)
        
        # Вычисляем процент изменения
        def calculate_trend(current, previous):
            if previous == 0:
                return 0
            return round(((current - previous) / previous) * 100, 1)
        
        # Получаем информацию о тарифе пользователя
        try:
            from apps.billing.utils import get_user_plan_info, update_plan_emails_sent
            update_plan_emails_sent(request.user)
            plan_info = get_user_plan_info(request.user)
        except Exception as e:
            plan_info = None
        
        return Response({
            'sent': total_sent,
            'delivered': total_delivered,
            'opened': total_opened,
            'clicked': total_clicked,
            'sentTrend': calculate_trend(week_sent, prev_week_sent),
            'deliveredTrend': calculate_trend(week_delivered, prev_week_delivered),
            'openedTrend': calculate_trend(week_opened, prev_week_opened),
            'clickedTrend': calculate_trend(week_clicked, prev_week_clicked),
            'newSubscribers': 0,  # Пока не реализовано
            'subscribersTrend': 0,  # Пока не реализовано
            'planInfo': plan_info
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Повторная попытка отправки кампании"""
        campaign = self.get_object()

        # Проверяем, что кампания действительно в статусе ошибки
        if campaign.status != Campaign.STATUS_FAILED:
            return Response(
                {'detail': 'Повторная отправка возможна только для кампаний со статусом "Ошибка"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем обязательные поля
        missing = []
        
        # Проверяем простые поля
        for field in ('name', 'template', 'sender_email', 'subject'):
            value = getattr(campaign, field)
            if not value:
                missing.append(field)
        
        # Проверяем sender_name через sender_email
        if not campaign.sender_email:
            missing.append('sender_email')
        
        # Проверяем списки контактов
        if not campaign.contact_lists.exists():
            missing.append('contact_lists')
            
        # Проверяем шаблон
        if not campaign.template:
            missing.append('template')
            
        # Проверяем email отправителя
        if not campaign.sender_email:
            missing.append('sender_email')

        if missing:
            return Response(
                {'detail': f'Не заполнены: {", ".join(missing)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем наличие контента в шаблоне
        if not campaign.template.html_content:
            return Response(
                {'detail': 'Шаблон не содержит HTML-контента'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Очищаем предыдущие записи об отправке
            EmailTracking.objects.filter(campaign=campaign).delete()
            CampaignRecipient.objects.filter(campaign=campaign).delete()

            # Обновляем статус и запускаем отправку
            campaign.status = Campaign.STATUS_SENDING
            campaign.save(update_fields=['status'])
            
            # Запускаем отправку через Celery
            from apps.campaigns.tasks import send_campaign
            task = send_campaign.delay(str(campaign.id))
            campaign.celery_task_id = task.id
            campaign.save(update_fields=['celery_task_id'])

            return Response({
                'detail': 'Кампания запущена повторно.',
                'status': 'sending',
                'status_display': campaign.get_status_display()
            })

        except Exception as e:
            campaign.status = Campaign.STATUS_FAILED
            campaign.save(update_fields=['status'])
            return Response(
                {'detail': f'Ошибка при повторной отправке: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def task_status(self, request, pk=None):
        """Проверка статуса задачи Celery"""
        campaign = self.get_object()
        
        if not campaign.celery_task_id:
            return Response({
                'task_id': None,
                'status': 'no_task',
                'message': 'Нет активной задачи'
            })
        
        try:
            from celery.result import AsyncResult
            task_result = AsyncResult(campaign.celery_task_id)
            
            # Получаем дополнительную информацию
            info = {
                'task_id': campaign.celery_task_id,
                'status': task_result.state,
                'ready': task_result.ready(),
                'successful': task_result.successful() if task_result.ready() else None,
                'failed': task_result.failed() if task_result.ready() else None,
            }
            
            # Если задача завершена, добавляем результат
            if task_result.ready():
                try:
                    result = task_result.result
                    info['result'] = result
                except Exception as e:
                    info['result_error'] = str(e)
            
            # Если задача в процессе, добавляем прогресс
            if task_result.state == 'PROGRESS':
                info['progress'] = task_result.info
            
            return Response(info)
            
        except Exception as e:
            return Response({
                'task_id': campaign.celery_task_id,
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def system_status(self, request):
        """Проверка статуса системы Celery"""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            
            # Проверяем активных workers
            stats = inspect.stats()
            active_tasks = inspect.active()
            registered_tasks = inspect.registered()
            
            # Проверяем очереди
            from django.core.cache import cache
            redis_info = {}
            try:
                import redis
                r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
                redis_info = {
                    'connected': r.ping(),
                    'queue_lengths': {}
                }
                
                # Проверяем длину очередей
                for queue in ['campaigns', 'email', 'default']:
                    try:
                        redis_info['queue_lengths'][queue] = r.llen(queue)
                    except:
                        redis_info['queue_lengths'][queue] = 'unknown'
            except Exception as e:
                redis_info = {'error': str(e)}
            
            return Response({
                'workers': {
                    'count': len(stats) if stats else 0,
                    'active': bool(stats),
                    'details': stats
                },
                'tasks': {
                    'active': len(active_tasks.get('active', [])) if active_tasks else 0,
                    'registered': len(registered_tasks.get('registered', [])) if registered_tasks else 0
                },
                'redis': redis_info,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response({
                'error': 'Ошибка проверки статуса системы',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CampaignListView(LoginRequiredMixin, TemplateView):
    """
    Рендерит страницу «Список кампаний».
    SPA на Alpine.js сама подгрузит их через API.
    """
    template_name = 'campaigns_list.html'


class CampaignFormView(LoginRequiredMixin, TemplateView):
    """
    Рендерит страницу «Создать/редактировать кампанию».
    """
    template_name = 'campaigns_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = kwargs.get('pk')
        
        if pk:
            try:
                campaign = Campaign.objects.get(pk=pk, user=self.request.user)
                # Преобразуем данные кампании в формат для фронтенда
                context['campaign'] = {
                    'id': str(campaign.id),
                    'name': campaign.name,
                    'subject': campaign.subject,
                    'sender_name': campaign.sender_email.sender_name if campaign.sender_email else '',
                    'reply_to': campaign.sender_email.reply_to if campaign.sender_email else '',
                    'status': campaign.status,
                    'scheduled_at': campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
                    'template': {
                        'id': str(campaign.template.id),
                        'title': campaign.template.title
                    } if campaign.template else None,
                    'sender_email': {
                        'id': str(campaign.sender_email.id),
                        'email': campaign.sender_email.email
                    } if campaign.sender_email else None,
                    'contact_lists': [
                        {
                            'id': str(cl.id),
                            'name': cl.name
                        } for cl in campaign.contact_lists.all()
                    ]
                }
            except Campaign.DoesNotExist:
                raise Http404("Кампания не найдена")
        
        return context


@require_GET
def track_email_open(request, campaign_id):
    """Обработчик открытия письма"""
    tracking_id = request.GET.get('tracking_id')
    if not tracking_id:
        raise Http404("Tracking ID is required")
        
    try:
        tracking = EmailTracking.objects.get(
            campaign_id=campaign_id,
            tracking_id=tracking_id
        )
        tracking.mark_as_opened(
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        # Return a 1x1 transparent pixel
        return HttpResponse(
            bytes.fromhex('47494638396101000100800000dbdbdb00000021f90401000000002c00000000010001000002024401003b'),
            content_type='image/gif'
        )
    except EmailTracking.DoesNotExist:
        raise Http404("Tracking record not found")

@require_GET
def track_email_click(request, campaign_id):
    """Обработчик клика по ссылке"""
    tracking_id = request.GET.get('tracking_id')
    url = request.GET.get('url')
    
    if not tracking_id:
        raise Http404("Tracking ID is required")
    if not url:
        raise Http404("URL parameter is required")
        
    try:
        tracking = EmailTracking.objects.get(
            campaign_id=campaign_id,
            tracking_id=tracking_id
        )
        tracking.mark_as_clicked(
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        # Redirect to the original URL
        return HttpResponseRedirect(url)
    except EmailTracking.DoesNotExist:
        raise Http404("Tracking record not found")
