# Интеграция с CloudPayments

## Обзор

Реализована полная интеграция с платежной системой CloudPayments для обработки оплаты тарифов. Система поддерживает одноразовые платежи и рекуррентные подписки.

## Основные компоненты

### 1. Модель CloudPaymentsTransaction

```python
class CloudPaymentsTransaction(models.Model):
    user = models.ForeignKey('accounts.User', ...)
    plan = models.ForeignKey(Plan, ...)
    cloudpayments_id = models.CharField(unique=True)
    amount = models.DecimalField()
    currency = models.CharField(default='RUB')
    status = models.CharField(choices=STATUS_CHOICES)
    # ... другие поля
```

### 2. Сервис CloudPaymentsService

Основной класс для работы с API CloudPayments:

- `create_payment()` - создание платежа
- `verify_signature()` - проверка подписи webhook
- `process_webhook()` - обработка уведомлений
- `get_transaction_status()` - получение статуса транзакции
- `refund_transaction()` - возврат средств
- `create_recurring_payment()` - рекуррентные платежи

### 3. API Endpoints

```
POST /billing/api/cloudpayments/create_payment/
GET  /billing/api/cloudpayments/transaction_status/
GET  /billing/api/cloudpayments/transactions/
POST /billing/webhook/cloudpayments/
```

## Настройка

### 1. Настройки в админке

В админке Django необходимо настроить:

- `cloudpayments_public_id` - Public ID из личного кабинета CloudPayments
- `cloudpayments_api_secret` - API Secret для подписи webhook
- `cloudpayments_test_mode` - тестовый режим (True/False)

### 2. Webhook URL

В личном кабинете CloudPayments указать webhook URL:
```
https://yourdomain.com/billing/webhook/cloudpayments/
```

### 3. Настройки безопасности

- Проверка подписи всех webhook запросов
- Валидация данных транзакций
- Логирование всех операций

## Процесс оплаты

### 1. Создание платежа

```python
# Создаем платеж
payment_data = cloudpayments_service.create_payment(
    user=user,
    plan=plan,
    amount=plan.get_final_price()
)

# Перенаправляем на страницу оплаты
return redirect('billing:payment', transaction_id=payment_data['transaction_id'])
```

### 2. Страница оплаты

Пользователь попадает на страницу с виджетом CloudPayments, где может:
- Ввести данные карты
- Выбрать способ оплаты
- Подтвердить платеж

### 3. Обработка результата

После оплаты CloudPayments отправляет webhook с результатом:

```python
@csrf_exempt
def cloudpayments_webhook(request):
    data = request.POST.dict()
    signature = request.headers.get('X-Signature', '')
    
    result = cloudpayments_service.process_webhook(data, signature)
    
    if result.get('success'):
        # Активируем тариф
        return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'status': 'error'}, status=400)
```

### 4. Активация тарифа

При успешной оплате автоматически:
- Создается запись `PurchasedPlan`
- Обновляется текущий тариф пользователя
- Устанавливается срок действия (30 дней)

## Безопасность

### 1. Проверка подписи

```python
def verify_signature(self, data, signature):
    # Создаем строку для подписи
    sign_string = ""
    for key in sorted(data.keys()):
        if key != "Signature":
            sign_string += str(data[key]) + ";"
    
    # Создаем подпись
    expected_signature = hmac.new(
        self.api_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
```

### 2. Валидация данных

- Проверка существования транзакции
- Валидация суммы платежа
- Проверка принадлежности транзакции пользователю

### 3. Обработка ошибок

- Логирование всех ошибок
- Graceful handling исключений
- Информативные сообщения пользователю

## Команды управления

### Создание расширенных тарифов

```bash
# Создать все тарифы
python manage.py create_extended_plans

# Принудительно пересоздать тарифы
python manage.py create_extended_plans --force
```

### Обновление счётчиков

```bash
# Обновить счётчики писем
python manage.py update_email_counts
```

## Тестирование

### Тестовые карты CloudPayments

Для тестирования используйте:

- **Успешная оплата**: `4111 1111 1111 1111`
- **Недостаточно средств**: `4444 4444 4444 4444`
- **Карта заблокирована**: `4000 0000 0000 0002`

### Тестовый режим

В тестовом режиме:
- Все платежи проходят без реального списания
- Можно использовать тестовые карты
- Webhook отправляется в тестовом окружении

## Мониторинг

### Логирование

Все операции логируются:
- Создание платежей
- Обработка webhook
- Ошибки и исключения
- Активация тарифов

### Статистика

В админке доступна статистика:
- Количество транзакций
- Суммы платежей
- Успешность операций
- Популярность тарифов

## Автопродление

### Настройка

В настройках биллинга:
- `auto_renewal_enabled` - включить автопродление
- `auto_renewal_days_before` - дней до истечения

### Процесс

1. За 3 дня до истечения тарифа система проверяет активные тарифы
2. Если включено автопродление, создается новый платеж
3. При успешной оплате тариф продлевается автоматически

## Возврат средств

### API для возврата

```python
# Полный возврат
result = cloudpayments_service.refund_transaction(transaction_id)

# Частичный возврат
result = cloudpayments_service.refund_transaction(
    transaction_id, 
    amount=100.00
)
```

### Автоматический возврат

При отмене тарифа в течение 14 дней:
- Автоматический возврат средств
- Деактивация тарифа
- Уведомление пользователя

## Интеграция с дашбордом

### Отображение информации

В дашборде показывается:
- Текущий тариф и его статус
- Остаток писем/дней
- История транзакций
- Кнопка для смены тарифа

### Уведомления

Система уведомляет о:
- Истечении тарифа
- Успешной оплате
- Ошибках платежа
- Автопродлении

## Развертывание

### 1. Миграции

```bash
python manage.py migrate billing
```

### 2. Создание тарифов

```bash
python manage.py create_extended_plans
```

### 3. Настройка CloudPayments

1. Получить Public ID и API Secret в личном кабинете
2. Настроить webhook URL
3. Указать настройки в админке Django

### 4. Тестирование

1. Включить тестовый режим
2. Протестировать оплату тестовыми картами
3. Проверить webhook
4. Переключить в продакшн режим

## Поддержка

### Документация CloudPayments

- [API документация](https://developers.cloudpayments.ru/)
- [Тестирование](https://developers.cloudpayments.ru/#testing)
- [Webhook](https://developers.cloudpayments.ru/#webhook)

### Логи и отладка

Все операции логируются в Django logs:
```python
import logging
logger = logging.getLogger(__name__)
logger.info(f"Payment created: {transaction.id}")
``` 