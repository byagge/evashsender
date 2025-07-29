from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
from .models import PlanType, Plan, PurchasedPlan, BillingSettings
from .serializers import (
    PlanTypeSerializer, PlanSerializer, PurchasedPlanSerializer,
    BillingSettingsSerializer, UserPlanInfoSerializer
)


class PlanTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API для типов тарифов"""
    queryset = PlanType.objects.filter(is_active=True)
    serializer_class = PlanTypeSerializer
    permission_classes = [permissions.AllowAny]


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """API для тарифных планов"""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтрация по типу плана
        plan_type = self.request.query_params.get('plan_type', None)
        if plan_type:
            queryset = queryset.filter(plan_type__name=plan_type)
        
        # Фильтрация по цене
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        return queryset.select_related('plan_type')
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Получить рекомендуемые тарифы"""
        plans = self.get_queryset().filter(is_featured=True)
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pricing_data(self, request):
        """Получить данные для калькулятора цен"""
        plans = self.get_queryset()
        
        # Группируем планы по типам
        pricing_data = {}
        for plan in plans:
            plan_type = plan.plan_type.name
            if plan_type not in pricing_data:
                pricing_data[plan_type] = []
            
            pricing_data[plan_type].append({
                'subscribers': plan.subscribers,
                'emails': plan.emails_per_month,
                'price': float(plan.get_final_price())
            })
        
        return Response(pricing_data)


class PurchasedPlanViewSet(viewsets.ModelViewSet):
    """API для купленных тарифов"""
    serializer_class = PurchasedPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PurchasedPlan.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Получить текущий активный тариф"""
        current_plan = self.get_queryset().filter(
            is_active=True,
            end_date__gt=timezone.now()
        ).first()
        
        if current_plan:
            serializer = self.get_serializer(current_plan)
            return Response(serializer.data)
        else:
            return Response({'detail': 'Активный тариф не найден'}, status=404)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """История покупок"""
        history = self.get_queryset().order_by('-start_date')
        serializer = self.get_serializer(history, many=True)
        return Response(serializer.data)


class BillingSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    """API для настроек биллинга"""
    queryset = BillingSettings.objects.all()
    serializer_class = BillingSettingsSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        return BillingSettings.get_settings()


class UserPlanInfoViewSet(viewsets.ViewSet):
    """API для информации о плане пользователя"""
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """Получить информацию о текущем плане пользователя"""
        user = request.user
        
        # Получаем настройки биллинга
        settings = BillingSettings.get_settings()
        
        # Если у пользователя нет плана, используем бесплатный
        if not user.current_plan:
            # Создаем временный объект плана с бесплатными лимитами
            from .models import Plan
            free_plan = Plan(
                title="Бесплатный",
                subscribers=settings.free_plan_subscribers,
                emails_per_month=settings.free_plan_emails,
                max_emails_per_day=settings.free_plan_daily_limit,
                price=0
            )
        else:
            free_plan = user.current_plan
        
        # Проверяем истечение плана
        is_expired = user.plan_expiry and user.plan_expiry < timezone.now()
        days_remaining = 0
        if user.plan_expiry and not is_expired:
            days_remaining = (user.plan_expiry - timezone.now()).days
        
        data = {
            'current_plan': free_plan,
            'plan_expiry': user.plan_expiry,
            'emails_sent_today': user.emails_sent_today,
            'has_exceeded_daily_limit': user.has_exceeded_daily_limit(),
            'days_remaining': days_remaining,
            'is_plan_expired': is_expired
        }
        
        serializer = UserPlanInfoSerializer(data)
        return Response(serializer.data)


# Views для покупки тарифов
@login_required
def confirm_plan(request):
    """Страница подтверждения покупки тарифа"""
    plan_id = request.GET.get('plan_id')
    if not plan_id:
        messages.error(request, 'Тариф не выбран')
        return redirect('pricing')
    
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    
    # Если тариф бесплатный - активируем сразу
    if plan.price == 0:
        return activate_free_plan(request, plan)
    
    # Для платных тарифов показываем страницу подтверждения
    context = {
        'plan': plan,
        'final_price': plan.get_final_price(),
        'duration_days': 30,  # Можно сделать настраиваемым
    }
    
    if request.method == 'POST':
        return process_plan_purchase(request, plan)
    
    return render(request, 'billing/confirm_plan.html', context)


@login_required
def activate_free_plan(request, plan=None):
    """Активация бесплатного тарифа"""
    if not plan:
        plan = Plan.objects.filter(price=0, is_active=True).first()
    
    if not plan:
        messages.error(request, 'Бесплатный тариф недоступен')
        return redirect('pricing')
    
    user = request.user
    
    # Создаем запись о покупке бесплатного тарифа
    PurchasedPlan.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=365),  # Год бесплатно
        is_active=True,
        amount_paid=0,
        payment_method='free'
    )
    
    # Обновляем текущий план пользователя
    user.current_plan = plan
    user.plan_expiry = timezone.now() + timedelta(days=365)
    user.save()
    
    messages.success(request, f'Тариф "{plan.title}" успешно активирован!')
    return redirect('dashboard')


@login_required
def process_plan_purchase(request, plan):
    """Обработка покупки платного тарифа"""
    user = request.user
    
    # Здесь можно добавить интеграцию с платежной системой
    # Пока делаем тестовую покупку
    
    # Создаем запись о покупке
    purchased_plan = PurchasedPlan.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True,
        amount_paid=plan.get_final_price(),
        payment_method='test',  # В реальности здесь будет способ оплаты
        transaction_id=f'test_{timezone.now().strftime("%Y%m%d_%H%M%S")}'
    )
    
    # Обновляем текущий план пользователя
    user.current_plan = plan
    user.plan_expiry = purchased_plan.end_date
    user.save()
    
    messages.success(request, f'Тариф "{plan.title}" успешно приобретен!')
    return redirect('dashboard')


@login_required
def plan_history(request):
    """История покупок тарифов"""
    purchases = PurchasedPlan.objects.filter(user=request.user).order_by('-start_date')
    return render(request, 'billing/plan_history.html', {'purchases': purchases})


# API для проверки авторизации
@csrf_exempt
def check_auth_status(request):
    """API для проверки статуса авторизации"""
    if request.user.is_authenticated:
        return JsonResponse({
            'is_authenticated': True,
            'user_email': request.user.email
        })
    else:
        return JsonResponse({
            'is_authenticated': False
        })
