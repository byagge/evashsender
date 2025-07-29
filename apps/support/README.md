# Система тикетов поддержки

Полнофункциональная система тикетов для обработки обращений пользователей в поддержку.

## Возможности

### Для пользователей:
- ✅ Создание новых тикетов с выбором категории и приоритета
- ✅ Просмотр своих тикетов и их статусов
- ✅ Добавление ответов к открытым тикетам
- ✅ Просмотр истории переписки
- ✅ Фильтрация и поиск по тикетам

### Для сотрудников поддержки:
- ✅ Просмотр всех тикетов в системе
- ✅ Назначение тикетов на себя или других сотрудников
- ✅ Изменение статуса тикетов (открыт, в работе, решён, закрыт)
- ✅ Добавление внутренних заметок
- ✅ Просмотр статистики по тикетам
- ✅ Фильтрация по статусу, приоритету, категории

## Модели данных

### Ticket (Тикет)
- **id**: UUID первичный ключ
- **user**: Связь с пользователем (создатель тикета)
- **category**: Категория тикета (опционально)
- **subject**: Тема тикета
- **description**: Описание проблемы
- **status**: Статус (открыт, в работе, ожидает ответа, решён, закрыт)
- **priority**: Приоритет (низкий, средний, высокий, срочный)
- **assigned_to**: Назначенный сотрудник (опционально)
- **created_at/updated_at**: Даты создания и обновления
- **resolved_at/closed_at**: Даты решения и закрытия
- **user_agent/ip_address**: Метаданные

### TicketMessage (Сообщение)
- **id**: UUID первичный ключ
- **ticket**: Связь с тикетом
- **author**: Автор сообщения
- **message**: Текст сообщения
- **is_internal**: Внутреннее сообщение (видно только сотрудникам)
- **is_staff_reply**: Ответ сотрудника (автоматически определяется)
- **created_at/updated_at**: Даты создания и обновления
- **attachment**: Вложение (опционально)

### TicketCategory (Категория)
- **name**: Название категории
- **description**: Описание
- **color**: Цвет для отображения
- **is_active**: Активна ли категория
- **sort_order**: Порядок сортировки

### TicketAttachment (Вложение)
- **file**: Файл
- **filename**: Имя файла
- **file_size**: Размер файла
- **mime_type**: MIME тип
- **uploaded_at**: Дата загрузки

## API Endpoints

### Тикеты
- `GET /support/api/tickets/` - Список тикетов
- `POST /support/api/tickets/` - Создание тикета
- `GET /support/api/tickets/{id}/` - Детали тикета
- `PUT /support/api/tickets/{id}/` - Обновление тикета (только сотрудники)
- `GET /support/api/tickets/{id}/detail/` - Детали с сообщениями
- `POST /support/api/tickets/{id}/reply/` - Добавить ответ
- `POST /support/api/tickets/{id}/close/` - Закрыть тикет (только сотрудники)
- `POST /support/api/tickets/{id}/resolve/` - Решить тикет (только сотрудники)
- `POST /support/api/tickets/{id}/assign/` - Назначить сотрудника (только сотрудники)
- `GET /support/api/tickets/my_tickets/` - Мои тикеты
- `GET /support/api/tickets/stats/` - Статистика (только сотрудники)

### Категории
- `GET /support/api/categories/` - Список категорий

### Сообщения
- `GET /support/api/tickets/{ticket_id}/messages/` - Сообщения тикета
- `POST /support/api/tickets/{ticket_id}/messages/` - Добавить сообщение

## Права доступа

### Пользователи:
- Видят только свои тикеты
- Могут создавать новые тикеты
- Могут отвечать на открытые тикеты
- Не видят внутренние сообщения

### Сотрудники (is_staff=True):
- Видят все тикеты в системе
- Могут назначать тикеты на себя и других
- Могут изменять статус тикетов
- Могут добавлять внутренние сообщения
- Видят статистику по тикетам

## Установка и настройка

1. Приложение уже добавлено в `INSTALLED_APPS`
2. URL маршруты подключены в `core/urls.py`
3. Создайте миграции: `python manage.py makemigrations support`
4. Примените миграции: `python manage.py migrate`
5. Инициализируйте категории: `python manage.py init_support`

## Использование

### Создание тикета пользователем:
```python
from apps.support.models import Ticket

ticket = Ticket.objects.create(
    user=request.user,
    subject="Проблема с отправкой",
    description="Не могу отправить рассылку...",
    category=category,
    priority=Ticket.PRIORITY_MEDIUM
)
```

### Добавление ответа:
```python
from apps.support.models import TicketMessage

message = TicketMessage.objects.create(
    ticket=ticket,
    author=request.user,
    message="Ваш ответ здесь..."
)
```

### Получение статистики:
```python
from apps.support.models import Ticket

stats = {
    'total': Ticket.objects.count(),
    'open': Ticket.objects.filter(status=Ticket.STATUS_OPEN).count(),
    'resolved': Ticket.objects.filter(status=Ticket.STATUS_RESOLVED).count(),
}
```

## Интерфейс

Система имеет современный веб-интерфейс на Tailwind CSS с Alpine.js:
- Адаптивный дизайн
- Модальные окна для создания тикетов и просмотра деталей
- Фильтрация и поиск
- Статистика в реальном времени
- Интуитивная навигация

## Расширение

Система легко расширяется:
- Добавление новых статусов и приоритетов
- Интеграция с email уведомлениями
- Добавление SLA (Service Level Agreement)
- Интеграция с внешними системами
- Добавление рейтинга качества поддержки 