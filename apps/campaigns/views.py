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
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Если это черновик, сохраняем все поля как есть
        if instance.status == Campaign.STATUS_DRAFT:
            self.perform_update(serializer)
            return Response(serializer.data)
            
        # Для других статусов выполняем полную валидацию
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        campaign = self.get_object()

        if campaign.status != Campaign.STATUS_DRAFT:
            return Response({'detail': 'Можно отправить только черновик.'},
                            status=status.HTTP_400_BAD_REQUEST)

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
        from core.apps.campaigns.models import CampaignRecipient
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
        # --- КОНЕЦ ОГРАНИЧЕНИЯ ---

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

        # Проверяем статус доверенного пользователя
        if not request.user.is_trusted_user:
            # Если пользователь не доверенный, отправляем на модерацию
            campaign.status = Campaign.STATUS_PENDING
            campaign.save(update_fields=['status'])
            return Response({
                'detail': 'Рассылка отправлена на модерацию.',
                'status': 'pending',
                'message': 'Ваша рассылка будет отправлена после проверки модератором.'
            })
        else:
            # Если пользователь доверенный, отправляем сразу
            campaign.status = Campaign.STATUS_SENDING
            campaign.save(update_fields=['status'])
            self._send_sync(campaign)
            return Response({
                'detail': 'Кампания запущена.',
                'status': 'sending'
            })

    def _send_sync(self, campaign):
        try:
            # Get all contacts from all contact lists
            contacts = set()
            for contact_list in campaign.contact_lists.all():
                contacts.update(contact_list.contacts.all())

            # Send email to each contact
            for contact in contacts:
                # Create tracking record
                tracking = EmailTracking.objects.create(
                    campaign=campaign,
                    contact=contact,
                    tracking_id=str(uuid.uuid4())
                )

                # Prepare email content with tracking
                html_content = campaign.template.html_content
                if campaign.content:
                    html_content = html_content.replace('{{content}}', campaign.content)

                # Add tracking pixel
                tracking_pixel = f'<img src="/campaigns/{campaign.id}/track-open/?tracking_id={tracking.tracking_id}" width="1" height="1" />'
                html_content = html_content.replace('</body>', f'{tracking_pixel}</body>')

                # Replace tracking links
                html_content = html_content.replace('href="', f'href="/campaigns/{campaign.id}/track-click/?tracking_id={tracking.tracking_id}&url=')

                # Send email
                email = EmailMultiAlternatives(
                    subject=campaign.subject,
                    body=html_content,  # Plain text version
                    from_email=f"{campaign.sender_email.sender_name} <{campaign.sender_email.email}>",
                    to=[contact.email],
                    reply_to=[campaign.sender_email.reply_to] if campaign.sender_email.reply_to else None
                )
                email.attach_alternative(html_content, "text/html")
                email.send()

                # Mark as sent in CampaignRecipient
                CampaignRecipient.objects.create(
                    campaign=campaign,
                    contact=contact,
                    is_sent=True,
                    sent_at=timezone.now()
                )

                # Mark as delivered
                tracking.mark_as_delivered()

            # Update campaign status
            campaign.status = Campaign.STATUS_SENT
            campaign.sent_at = timezone.now()
            campaign.save(update_fields=['status', 'sent_at'])

        except Exception as e:
            campaign.status = Campaign.STATUS_FAILED
            campaign.save(update_fields=['status'])
            raise e

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
            'subscribersTrend': 0  # Пока не реализовано
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
            
            # Запускаем отправку в отдельном потоке
            import threading
            thread = threading.Thread(target=self._send_sync, args=(campaign,))
            thread.start()

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
