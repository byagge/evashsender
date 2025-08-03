from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from apps.billing.models import Plan, PlanType

# Create your views here.

def landing_page(request):
    return render(request, 'landing.html')


def pricing_page(request):
    """Страница тарифов с динамической загрузкой данных"""
    return render(request, 'pricing.html')


def get_plans_api(request):
    """API для получения тарифов для pricing.html"""
    try:
        # Получаем все активные тарифы
        plans = Plan.objects.filter(is_active=True).select_related('plan_type').order_by('sort_order')
        
        print(f"DEBUG: Found {plans.count()} plans")
        
        # Группируем по типам
        plans_data = {
            'free': [],
            'subscribers': [],
            'letters': []
        }
        
        for plan in plans:
            print(f"DEBUG: Processing plan {plan.id}: {plan.title} ({plan.plan_type.name})")
            plan_data = {
                'id': plan.id,
                'title': plan.title,
                'price': float(plan.get_final_price()),
                'subscribers': plan.subscribers,
                'emails_per_month': plan.emails_per_month,
                'max_emails_per_day': plan.max_emails_per_day,
                'is_featured': plan.is_featured,
                'sort_order': plan.sort_order
            }
            
            if plan.plan_type.name == 'Free':
                plans_data['free'].append(plan_data)
            elif plan.plan_type.name == 'Subscribers':
                plans_data['subscribers'].append(plan_data)
            elif plan.plan_type.name == 'Letters':
                plans_data['letters'].append(plan_data)
        
        print(f"DEBUG: Final data - Free: {len(plans_data['free'])}, Subscribers: {len(plans_data['subscribers'])}, Letters: {len(plans_data['letters'])}")
        
        response = JsonResponse({
            'success': True,
            'plans': plans_data
        })
        response['Content-Type'] = 'application/json'
        return response
        
    except Exception as e:
        print(f"DEBUG: Error in get_plans_api: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def purchase_confirmation_page(request):
    return render(request, 'purchase_confirmation.html')


def index(request):
    """Перенаправление для авторизованных пользователей на dashboard"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    return redirect('dashboard')

@login_required
def purchase_confirmation(request):
    """Страница подтверждения покупки"""
    plan_id = request.GET.get('plan_id')
    if not plan_id:
        messages.error(request, 'Тариф не выбран')
        return redirect('main:pricing')
    
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    
    context = {
        'plan': plan,
    }
    
    return render(request, 'purchase_confirmation.html', context)

@login_required
def purchase_success(request):
    """Страница успешной покупки"""
    plan_id = request.GET.get('plan_id')
    transaction_id = request.GET.get('transaction_id', 'TEST-123456')
    
    if plan_id:
        plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    else:
        plan = None
    
    context = {
        'plan': plan,
        'transaction_id': transaction_id,
    }
    
    return render(request, 'purchase_success.html', context)
