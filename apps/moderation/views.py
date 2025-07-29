from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponseServerError
from django.utils import timezone
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import CampaignModeration
from apps.campaigns.models import Campaign
from apps.accounts.models import User

def is_moderator(user):
    return user.is_staff

@login_required
@user_passes_test(is_moderator)
def moderation_dashboard(request):
    try:
        # Получаем кампании из CampaignModeration
        moderated_campaigns = CampaignModeration.objects.select_related(
            'campaign', 'campaign__user', 'moderator'
        ).all()
        
        # Получаем кампании, которые находятся в статусе pending
        pending_campaigns = Campaign.objects.filter(
            status='pending'
        ).select_related('user', 'template').prefetch_related('contact_lists')
        
        # Создаем записи в CampaignModeration для новых pending кампаний
        for campaign in pending_campaigns:
            # Проверяем, нет ли уже записи в CampaignModeration
            if not CampaignModeration.objects.filter(campaign=campaign).exists():
                CampaignModeration.objects.create(
                    campaign=campaign,
                    status='pending',
                    created_at=timezone.now()
                )
        
        # Обновляем список модерированных кампаний
        moderated_campaigns = CampaignModeration.objects.select_related(
            'campaign', 'campaign__user', 'moderator'
        ).all()
        
        # Prepare campaign data for the template
        campaigns_data = []
        
        # Добавляем данные из CampaignModeration
        for moderation in moderated_campaigns:
            campaign = moderation.campaign
            # Подсчитываем общее количество получателей из всех списков контактов
            total_recipients = sum(list.total_contacts for list in campaign.contact_lists.all())
            
            campaign_data = {
                'id': str(campaign.id),  # Convert UUID to string
                'name': campaign.name,
                'subject': campaign.subject,
                'status': moderation.status,
                'sender_email': campaign.sender_email.email if campaign.sender_email else None,
                'user_id': str(campaign.user.id) if campaign.user else None,
                'user_name': campaign.user.full_name if campaign.user else None,
                'user_email': campaign.user.email if campaign.user else None,
                'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
                'auto_send_at': moderation.auto_send_at.isoformat() if moderation.auto_send_at else None,
                'rejection_reason': moderation.rejection_reason,
                'is_trusted': campaign.user.is_trusted_user if campaign.user else False,
                'recipients': total_recipients,
                'lists': [list.name for list in campaign.contact_lists.all()],
                'preview_html': campaign.template.html_content if campaign.template else ''
            }
            campaigns_data.append(campaign_data)
        
        context = {
            'campaigns_json': json.dumps(campaigns_data, cls=DjangoJSONEncoder),
            'pending_count': len([c for c in campaigns_data if c['status'] == 'pending'])
        }
        return render(request, 'moderation/dashboard.html', context)
    except Exception as e:
        # Handle error without debug print
        return HttpResponseServerError("Internal server error")

@login_required
@user_passes_test(is_moderator)
def approve_campaign(request, campaign_id):
    if request.method == 'POST':
        moderation = get_object_or_404(CampaignModeration, campaign_id=campaign_id)
        moderation.approve(request.user)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@user_passes_test(is_moderator)
def reject_campaign(request, campaign_id):
    if request.method == 'POST':
        moderation = get_object_or_404(CampaignModeration, campaign_id=campaign_id)
        reason = request.POST.get('reason')
        if not reason:
            return JsonResponse({'status': 'error', 'message': 'Причина отклонения обязательна'}, status=400)
        moderation.reject(request.user, reason)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
@user_passes_test(is_moderator)
def mark_trusted_user(request, user_id):
    if request.method == 'POST':
        try:
            # Проверяем, что user_id не undefined и является валидным UUID
            if not user_id or user_id == 'undefined':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Неверный ID пользователя'
                }, status=400)
                
            user = get_object_or_404(User, id=user_id)
            user.is_trusted_user = True
            user.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Пользователь отмечен как доверенный'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    return JsonResponse({
        'status': 'error',
        'message': 'Метод не поддерживается'
    }, status=405)

@login_required
@user_passes_test(is_moderator)
def search_campaigns(request):
    query = request.GET.get('q', '')
    status = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    
    campaigns = CampaignModeration.objects.select_related(
        'campaign', 'campaign__user', 'moderator'
    )
    
    if query:
        campaigns = campaigns.filter(
            Q(campaign__name__icontains=query) |
            Q(campaign__subject__icontains=query) |
            Q(campaign__user__full_name__icontains=query)
        )
    
    if status and status != 'all':
        campaigns = campaigns.filter(status=status)
        
    if user_filter:
        campaigns = campaigns.filter(campaign__user__full_name__icontains=user_filter)
    
    campaigns_data = []
    for moderation in campaigns:
        campaign = moderation.campaign
        campaign_data = {
            'id': campaign.id,
            'name': campaign.name,
            'subject': campaign.subject,
            'status': moderation.status,
            'sender_email': campaign.sender_email,
            'user_name': campaign.user.full_name,
            'user_email': campaign.user.email,
            'created_at': campaign.created_at.isoformat(),
            'auto_send_at': moderation.auto_send_at.isoformat() if moderation.auto_send_at else None,
            'rejection_reason': moderation.rejection_reason,
            'is_trusted': campaign.user.is_trusted_user,
            'recipients': campaign.recipients_count,
            'lists': [list.name for list in campaign.contact_lists.all()],
            'preview_html': campaign.preview_html
        }
        campaigns_data.append(campaign_data)
    
    return JsonResponse({
        'campaigns': campaigns_data
    }) 