# Система учёта отправленных писем в тарифах

## Обзор

Реализована система учёта отправленных писем для тарифов с лимитом писем (тип "Letters"). Система автоматически отслеживает количество фактически отправленных писем и показывает пользователю остаток.

## Основные компоненты

### 1. Модель PurchasedPlan

Добавлено поле `emails_sent` для учёта отправленных писем:

```python
emails_sent = models.PositiveIntegerField(default=0, help_text="Количество отправленных писем")
```

### 2. Методы модели PurchasedPlan

- `get_emails_remaining()` - возвращает количество оставшихся писем
- `can_send_emails(count)` - проверяет, можно ли отправить указанное количество писем
- `add_emails_sent(count)` - добавляет количество отправленных писем

### 3. Утилиты (apps/billing/utils.py)

- `get_user_active_plan(user)` - получает активный тариф пользователя
- `get_user_emails_remaining(user)` - получает остаток писем
- `update_plan_emails_sent(user)` - обновляет счётчик на основе фактических отправок
- `get_user_plan_info(user)` - получает полную информацию о тарифе

## Как это работает

### 1. При отправке письма

В задаче `send_single_email` автоматически обновляется счётчик:

```python
# Обновляем счётчик отправленных писем в тарифе
try:
    from apps.billing.utils import add_emails_sent_to_plan
    add_emails_sent_to_plan(campaign.user, 1)
except Exception as e:
    print(f"Error updating email count: {e}")
```

### 2. Проверка лимитов перед отправкой

В задаче `send_campaign` проверяются лимиты тарифа:

```python
# Проверяем лимиты тарифа перед отправкой
try:
    from apps.billing.utils import can_user_send_emails, get_user_plan_info
    plan_info = get_user_plan_info(user)
    
    if plan_info['has_plan'] and plan_info['plan_type'] == 'Letters':
        if not can_user_send_emails(user, total_contacts):
            return {'error': f'Недостаточно писем в тарифе'}
except Exception as e:
    print(f"Error checking plan limits: {e}")
```

### 3. Отображение в дашборде

Дашборд показывает:
- Название тарифа
- Тип тарифа (с лимитом писем или подписчиков)
- Для тарифов с письмами: прогресс-бар использования и остаток
- Для тарифов с подписчиками: дни до истечения
- Количество писем, отправленных сегодня

## API Endpoints

### 1. Информация о тарифе пользователя

```
GET /billing/api/user-plan-info/
```

Возвращает:
```json
{
    "has_plan": true,
    "plan_name": "10 000 писем",
    "plan_type": "Letters",
    "emails_limit": 10000,
    "emails_sent": 5869,
    "emails_remaining": 4131,
    "days_remaining": 25,
    "is_expired": false,
    "emails_sent_today": 150,
    "has_exceeded_daily_limit": false
}
```

### 2. Статистика кампаний (обновлена)

```
GET /campaigns/api/campaigns/stats/
```

Теперь также возвращает `planInfo` в ответе.

## Команды управления

### Обновление счётчиков

```bash
# Обновить счётчики для всех пользователей
python manage.py update_email_counts

# Обновить счётчики для конкретного пользователя
python manage.py update_email_counts --user user@example.com

# Показать что будет обновлено без внесения изменений
python manage.py update_email_counts --dry-run
```

## Миграции

Создана миграция для добавления поля `emails_sent`:

```bash
python manage.py migrate billing
```

## Типы тарифов

### 1. Тарифы с лимитом писем (Letters)

- Лимит по количеству писем
- Счётчик уменьшается при каждой отправке
- Тариф заканчивается, когда остаток равен нулю
- Пример: "10 000 писем"

### 2. Тарифы с лимитом подписчиков (Subscribers)

- Лимит по времени действия
- Счётчик писем не учитывается
- Тариф заканчивается по истечении срока
- Пример: "10 000 подписчиков"

## Отладка

### Проверка счётчиков

```python
from apps.billing.utils import get_user_plan_info, update_plan_emails_sent

# Обновить счётчик
update_plan_emails_sent(user)

# Получить информацию
plan_info = get_user_plan_info(user)
print(f"Отправлено: {plan_info['emails_sent']}")
print(f"Осталось: {plan_info['emails_remaining']}")
```

### Проверка фактических отправок

```python
from apps.campaigns.models import EmailTracking
from apps.billing.models import PurchasedPlan

# Получить активный тариф
plan = PurchasedPlan.objects.filter(user=user, is_active=True).first()

# Подсчитать фактически отправленные письма
actual_sent = EmailTracking.objects.filter(
    campaign__user=user,
    sent_at__gte=plan.start_date,
    sent_at__lte=plan.end_date
).count()

print(f"Счётчик в тарифе: {plan.emails_sent}")
print(f"Фактически отправлено: {actual_sent}")
```

## Безопасность

- Все операции с счётчиками выполняются в транзакциях
- Проверка лимитов происходит перед отправкой
- Обработка ошибок для предотвращения сбоев
- Логирование всех операций с счётчиками 