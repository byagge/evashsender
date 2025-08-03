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
from .models import PlanType, Plan, PurchasedPlan, BillingSettings, CloudPaymentsTransaction
from .serializers import (
    PlanTypeSerializer, PlanSerializer, PurchasedPlanSerializer,
    BillingSettingsSerializer, UserPlanInfoSerializer
    # CloudPaymentsTransactionSerializer  # Временно отключено до применения миграций
)
# from .cloudpayments import cloudpayments_service  # Временно отключено до применения миграций


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
        """Получить историю тарифов"""
        plans = self.get_queryset().order_by('-start_date')
        serializer = self.get_serializer(plans, many=True)
        return Response(serializer.data)


# class CloudPaymentsViewSet(viewsets.ViewSet):
#     """API для работы с CloudPayments"""
#     permission_classes = [permissions.IsAuthenticated]
#     
#     @action(detail=False, methods=['post'])
#     def create_payment(self, request):
#         """Создать платеж"""
#         plan_id = request.data.get('plan_id')
#         amount = request.data.get('amount')
#         description = request.data.get('description')
#         
#         try:
#             plan = Plan.objects.get(id=plan_id, is_active=True)
#         except Plan.DoesNotExist:
#             return Response(
#                 {'error': 'Тариф не найден'}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         
#         # Создаем платеж
#         payment_data = cloudpayments_service.create_payment(
#             user=request.user,
#             plan=plan,
#             amount=amount,
#             description=description
#         )
#         
#         return Response(payment_data)
#     
#     @action(detail=False, methods=['get'])
#     def transaction_status(self, request):
#         """Получить статус транзакции"""
#         transaction_id = request.query_params.get('transaction_id')
#         
#         if not transaction_id:
#             return Response(
#                 {'error': 'ID транзакции не указан'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         
#         try:
#             transaction = CloudPaymentsTransaction.objects.get(
#                 id=transaction_id,
#                 user=request.user
#         )
#             serializer = CloudPaymentsTransactionSerializer(transaction)
#             return Response(serializer.data)
#         except CloudPaymentsTransaction.DoesNotExist:
#             return Response(
#                 {'error': 'Транзакция не найдена'}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )
#     
#     @action(detail=False, methods=['get'])
#     def transactions(self, request):
#         """Получить историю транзакций пользователя"""
#         transactions = CloudPaymentsTransaction.objects.filter(
#             user=request.user
#         ).order_by('-created_at')
#         
#         serializer = CloudPaymentsTransactionSerializer(transactions, many=True)
#         return Response(serializer.data)


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
        
        # Используем новую утилиту для получения информации о тарифе
        from .utils import get_user_plan_info, update_plan_emails_sent
        
        # Обновляем счётчик отправленных писем на основе фактических отправок
        update_plan_emails_sent(user)
        
        # Получаем информацию о тарифе
        plan_info = get_user_plan_info(user)
        
        # Добавляем дополнительную информацию
        plan_info.update({
            'emails_sent_today': user.emails_sent_today,
            'has_exceeded_daily_limit': user.has_exceeded_daily_limit(),
        })
        
        return Response(plan_info)


# Webhook для CloudPayments
# @csrf_exempt
# @require_http_methods(["POST"])
# def cloudpayments_webhook(request):
#     """Webhook для обработки уведомлений от CloudPayments"""
#     try:
#         # Получаем данные
#         data = request.POST.dict()
#         signature = request.headers.get('X-Signature', '')
#         
#         # Обрабатываем webhook
#         result = cloudpayments_service.process_webhook(data, signature)
#         
#         if result.get('success'):
#             return JsonResponse({'status': 'ok'})
#         else:
#             return JsonResponse(
#                 {'status': 'error', 'message': result.get('error')}, 
#                 status=400
#             )
#             
#     except Exception as e:
#         return JsonResponse(
#             {'status': 'error', 'message': str(e)}, 
#             status=500
#         )


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
    
    return render(request, 'purchase_confirmation.html', context)


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
    
    # Временно отключено до настройки CloudPayments
    # payment_data = cloudpayments_service.create_payment(
    #     user=user,
    #     plan=plan
    # )
    # return redirect('billing:payment', transaction_id=payment_data['transaction_id'])
    
    # Временное решение - создаем тестовую покупку
    from django.utils import timezone
    from datetime import timedelta
    
    purchased_plan = PurchasedPlan.objects.create(
        user=user,
        plan=plan,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=30),
        is_active=True,
        amount_paid=plan.get_final_price(),
        payment_method='test',
        transaction_id=f'test_{timezone.now().strftime("%Y%m%d_%H%M%S")}'
    )
    
    # Обновляем текущий план пользователя
    user.current_plan = plan
    user.plan_expiry = purchased_plan.end_date
    user.save()
    
    messages.success(request, f'Тариф "{plan.title}" успешно приобретен!')
    return redirect('dashboard')


# @login_required
# def payment_page(request, transaction_id):
#     """Страница оплаты"""
#     try:
#         transaction = CloudPaymentsTransaction.objects.get(
#             id=transaction_id,
#             user=request.user
#         )
#     except CloudPaymentsTransaction.DoesNotExist:
#         messages.error(request, 'Транзакция не найдена')
#         return redirect('dashboard')
#     
#     # Получаем настройки CloudPayments
#     settings = BillingSettings.get_settings()
#     
#     context = {
#         'transaction': transaction,
#         'cloudpayments_public_id': settings.cloudpayments_public_id,
#     }
#     
#     return render(request, 'billing/payment.html', context)


@login_required
def plan_history(request):
    """История тарифов пользователя"""
    purchased_plans = PurchasedPlan.objects.filter(
        user=request.user
    ).order_by('-start_date')
    
    return render(request, 'billing/plan_history.html', {
        'purchased_plans': purchased_plans
    })


@csrf_exempt
def check_auth_status(request):
    """Проверка статуса авторизации для AJAX запросов"""
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'email': request.user.email,
                'full_name': request.user.full_name
            }
        })
    else:
        return JsonResponse({'authenticated': False})
