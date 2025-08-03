# Интеграция CloudPayments

## Обзор

Система интегрирована с CloudPayments для обработки платежей за тарифы. Интеграция включает:

- Виджет CloudPayments для оплаты
- Рекуррентные платежи (подписки)
- Фискализация (чеки)
- Автоматическая активация тарифов после оплаты

## Компоненты

### 1. Frontend (purchase_confirmation.html)

**Файл:** `apps/main/templates/purchase_confirmation.html`

**Основные функции:**
- Инициализация виджета CloudPayments
- Формирование чека для фискализации
- Обработка успешных/неуспешных платежей
- Отправка данных на сервер для активации тарифа

**Ключевые особенности:**
```javascript
// Создание виджета с отключенными дополнительными методами оплаты
var payments = new cp.CloudPayments({
    yandexPaySupport: false,
    applePaySupport: false,
    googlePaySupport: false,
    masterPassSupport: false,
    tinkoffInstallmentSupport: false
});

// Запуск оплаты с рекуррентными платежами
payments.pay("charge", {
    publicId: 'test_api_00000000000000000000002',
    accountId: planData.userEmail,
    description: 'Подписка на тариф ' + planData.title + ' - vashsender',
    amount: planData.price,
    currency: 'RUB',
    invoiceId: 'PLAN-' + planData.id + '-' + Date.now(),
    data: data // Данные для рекуррентных платежей и чека
});
```

### 2. Backend (views.py)

**Файл:** `apps/billing/views.py`

**Основные функции:**
- `activate_payment()` - активация тарифа после успешной оплаты
- `confirm_plan()` - страница подтверждения покупки
- `plan_history()` - история тарифов

**Ключевые особенности:**
```python
@login_required
@require_http_methods(["POST"])
def activate_payment(request):
    """Активация тарифа после успешной оплаты через CloudPayments"""
    try:
        data = json.loads(request.body)
        plan_id = data.get('plan_id')
        payment_data = data.get('payment_data', {})
        
        # Создание записи о купленном тарифе
        with transaction.atomic():
            purchased_plan = PurchasedPlan.objects.create(
                user=user,
                plan=plan,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=30),
                is_active=True,
                amount_paid=plan.get_final_price(),
                payment_method='cloudpayments',
                transaction_id=payment_data.get('invoiceId'),
                cloudpayments_data=payment_data
            )
            
            # Обновление текущего плана пользователя
            user.current_plan = plan
            user.plan_expiry = purchased_plan.end_date
            user.save()
```

### 3. Модели данных

**Файл:** `apps/billing/models.py`

**Основные модели:**
- `PurchasedPlan` - купленные тарифы пользователей
- `CloudPaymentsTransaction` - транзакции CloudPayments
- `BillingSettings` - настройки биллинга

**Новые поля:**
```python
class PurchasedPlan(models.Model):
    # ... существующие поля ...
    cloudpayments_data = models.JSONField(
        null=True, 
        blank=True, 
        help_text=_("Данные от CloudPayments")
    )
```

### 4. Страница управления тарифами

**Файл:** `apps/billing/templates/billing/billing.html`

**Функции:**
- Отображение текущего тарифа
- История тарифов
- Управление автопродлением
- Переход к изменению тарифа

## Настройка

### 1. CloudPayments Public ID

Замените тестовый Public ID на ваш:
```javascript
publicId: 'test_api_00000000000000000000002', // Замените на ваш
```

### 2. Настройки в Django

В `apps/billing/models.py` в модели `BillingSettings`:
```python
cloudpayments_public_id = models.CharField(
    max_length=100, 
    blank=True, 
    help_text=_("Public ID CloudPayments")
)
cloudpayments_api_secret = models.CharField(
    max_length=100, 
    blank=True, 
    help_text=_("API Secret CloudPayments")
)
cloudpayments_test_mode = models.BooleanField(
    default=True, 
    help_text=_("Тестовый режим CloudPayments")
)
```

### 3. Миграции

Примените миграции для новых полей:
```bash
python manage.py makemigrations billing
python manage.py migrate billing
```

## Тестирование

### 1. Тестовые карты CloudPayments

Для тестирования используйте:
- **Успешная оплата:** 4111 1111 1111 1111
- **Неуспешная оплата:** 4444 4444 4444 4444
- **Любая будущая дата** (например, 12/25)
- **Любой CVC** (например, 123)

### 2. Тестовый файл

Создан файл `test_cloudpayments.html` для изолированного тестирования виджета.

## Безопасность

### 1. Content Security Policy

Система настроена для работы с CSP. Виджет CloudPayments загружается с `https://widget.cloudpayments.ru`.

### 2. CSRF Protection

Все POST запросы защищены CSRF токенами.

### 3. Аутентификация

Все endpoints требуют аутентификации пользователя.

## Мониторинг

### 1. Логирование

Включено детальное логирование:
```python
print(f"DEBUG: activate_payment called with user {request.user.email}")
print(f"DEBUG: Received data: {data}")
print(f"DEBUG: PurchasedPlan created with ID: {purchased_plan.id}")
```

### 2. Обработка ошибок

Все ошибки логируются и возвращают понятные сообщения пользователю.

## Расширение

### 1. Webhook поддержка

Подготовлена структура для webhook'ов CloudPayments:
```python
# @csrf_exempt
# @require_http_methods(["POST"])
# def cloudpayments_webhook(request):
#     """Webhook для обработки уведомлений от CloudPayments"""
```

### 2. Дополнительные методы оплаты

Можно включить дополнительные методы оплаты:
```javascript
var payments = new cp.CloudPayments({
    yandexPaySupport: true,
    applePaySupport: true,
    googlePaySupport: true,
    // ...
});
```

## Устранение неполадок

### 1. Ошибка 404 на /billing/

Проверьте, что URL добавлен в `apps/billing/urls.py`:
```python
path('', views.billing_page, name='billing_page'),
```

### 2. Ошибка 500 при активации тарифа

Проверьте:
- Применены ли миграции
- Импортирован ли `transaction` в `views.py`
- Правильность данных от CloudPayments

### 3. Виджет не загружается

Проверьте:
- Доступность `https://widget.cloudpayments.ru`
- Настройки CSP
- Консоль браузера на ошибки

## Ссылки

- [Документация CloudPayments](https://cloudpayments.ru/Docs)
- [Виджет CloudPayments](https://cloudpayments.ru/Docs/Widget)
- [Рекуррентные платежи](https://cloudpayments.ru/Docs/Recurrent) 