from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.billing.models import Plan

# Create your views here.

def landing(request):
    """Главная страница (landing)"""
    return render(request, 'landing.html')

def pricing(request):
    """Страница тарифов"""
    return render(request, 'pricing.html')

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
