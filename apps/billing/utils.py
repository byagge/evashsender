from django.utils import timezone
from django.db.models import Sum
from .models import PurchasedPlan
from apps.campaigns.models import EmailTracking


def get_user_active_plan(user):
    """Получить активный тариф пользователя"""
    return PurchasedPlan.objects.filter(
        user=user,
        is_active=True,
        end_date__gt=timezone.now()
    ).order_by('-start_date').first()


def get_user_emails_remaining(user):
    """Получить количество оставшихся писем для пользователя"""
    active_plan = get_user_active_plan(user)
    if not active_plan:
        return 0
    
    return active_plan.get_emails_remaining()


def get_user_emails_sent(user):
    """Получить количество отправленных писем пользователя в текущем тарифе"""
    active_plan = get_user_active_plan(user)
    if not active_plan:
        return 0
    
    return active_plan.emails_sent


def update_plan_emails_sent(user):
    """Обновить счётчик отправленных писем в тарифе на основе фактических отправок"""
    active_plan = get_user_active_plan(user)
    if not active_plan or active_plan.plan.plan_type.name != 'Letters':
        return
    
    # Подсчитываем фактически отправленные письма в период действия тарифа
    actual_sent = EmailTracking.objects.filter(
        campaign__user=user,
        sent_at__gte=active_plan.start_date,
        sent_at__lte=active_plan.end_date
    ).count()
    
    # Обновляем счётчик в тарифе
    if active_plan.emails_sent != actual_sent:
        active_plan.emails_sent = actual_sent
        active_plan.save(update_fields=['emails_sent'])
    
    return actual_sent


def can_user_send_emails(user, count=1):
    """Проверить, может ли пользователь отправить указанное количество писем"""
    active_plan = get_user_active_plan(user)
    if not active_plan:
        return False
    
    return active_plan.can_send_emails(count)


def add_emails_sent_to_plan(user, count=1):
    """Добавить количество отправленных писем к тарифу пользователя"""
    active_plan = get_user_active_plan(user)
    if not active_plan:
        return False
    
    active_plan.add_emails_sent(count)
    return True


def get_user_plan_info(user):
    """Получить полную информацию о тарифе пользователя"""
    active_plan = get_user_active_plan(user)
    if not active_plan:
        return {
            'has_plan': False,
            'plan_name': None,
            'plan_type': None,
            'emails_limit': 0,
            'emails_sent': 0,
            'emails_remaining': 0,
            'days_remaining': 0,
            'is_expired': True
        }
    
    emails_remaining = active_plan.get_emails_remaining()
    
    return {
        'has_plan': True,
        'plan_name': active_plan.plan.title,
        'plan_type': active_plan.plan.plan_type.name,
        'emails_limit': active_plan.plan.emails_per_month if active_plan.plan.plan_type.name == 'Letters' else None,
        'emails_sent': active_plan.emails_sent,
        'emails_remaining': emails_remaining,
        'days_remaining': active_plan.days_remaining(),
        'is_expired': active_plan.is_expired(),
        'start_date': active_plan.start_date,
        'end_date': active_plan.end_date
    } 