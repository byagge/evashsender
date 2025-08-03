# Руководство по Celery в продакшене

## Обзор улучшений

Система была оптимизирована для продакшена с добавлением:

1. **Таймауты и обработка ошибок** - все задачи имеют жесткие и мягкие лимиты времени
2. **Мониторинг зависших кампаний** - автоматическое обнаружение и исправление
3. **Периодические задачи** - автоматическая очистка и мониторинг
4. **Улучшенная обработка ошибок** - детальное логирование и retry механизмы
5. **Скрипт управления** - удобный запуск и мониторинг

## Запуск в продакшене

### 1. Использование скрипта (рекомендуется)

```bash
# Запуск
./start_celery_production.sh start

# Остановка
./start_celery_production.sh stop

# Перезапуск
./start_celery_production.sh restart

# Проверка статуса
./start_celery_production.sh status

# Запуск мониторинга (автоперезапуск)
./start_celery_production.sh monitor
```

### 2. Ручной запуск

```bash
# Worker
celery -A core worker --loglevel=info --concurrency=4 --queues=campaigns,email,default

# Beat scheduler (в отдельном терминале)
celery -A core beat --loglevel=info
```

## Мониторинг и диагностика

### Проверка зависших кампаний

```bash
# Проверка без исправления
python manage.py health_check

# Автоматическое исправление
python manage.py health_check --fix

# Проверка с кастомным таймаутом (15 минут)
python manage.py health_check --timeout=15 --fix
```

### Просмотр логов

```bash
# Логи worker
tail -f /var/log/vashsender/celery_worker.log

# Логи beat scheduler
tail -f /var/log/vashsender/celery_beat.log

# Общие логи
tail -f /var/log/vashsender/celery.log
```

### Проверка статуса задач

```bash
# Статус всех задач
celery -A core inspect active

# Статус очередей
celery -A core inspect stats

# Очистка очередей (осторожно!)
celery -A core purge
```

## Настройки таймаутов

### Текущие настройки:

- **send_campaign**: 30 минут максимум, 25 минут мягкий лимит
- **send_email_batch**: 10 минут максимум, 8 минут мягкий лимит  
- **send_single_email**: 5 минут максимум, 4 минуты мягкий лимит

### Изменение таймаутов:

Отредактируйте файл `apps/campaigns/tasks.py`:

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60, queue='campaigns', 
            time_limit=1800, soft_time_limit=1500)  # Измените эти значения
```

## Автоматический мониторинг

Система автоматически:

1. **Проверяет зависшие кампании** каждые 5 минут
2. **Очищает SMTP соединения** каждые 10 минут
3. **Перезапускает упавшие процессы** (если используется скрипт мониторинга)

## Решение проблем

### Кампания "зависла" в статусе "Отправляется"

1. **Проверьте логи**:
   ```bash
   tail -f /var/log/vashsender/celery_worker.log | grep "campaign_id"
   ```

2. **Запустите проверку здоровья**:
   ```bash
   python manage.py health_check --fix
   ```

3. **Проверьте статус Celery**:
   ```bash
   ./start_celery_production.sh status
   ```

### Письма не отправляются

1. **Проверьте SMTP настройки** в `core/settings/production.py`
2. **Проверьте логи SMTP**:
   ```bash
   tail -f /var/log/vashsender/celery_worker.log | grep "SMTP"
   ```
3. **Перезапустите Celery**:
   ```bash
   ./start_celery_production.sh restart
   ```

### Высокая нагрузка

1. **Увеличьте количество worker процессов**:
   ```bash
   celery -A core worker --concurrency=8
   ```

2. **Настройте очереди** в `core/celery.py`

3. **Мониторьте ресурсы**:
   ```bash
   htop
   iostat
   ```

## Логирование

Все логи сохраняются в `/var/log/vashsender/`:

- `celery_worker.log` - логи worker процессов
- `celery_beat.log` - логи beat scheduler
- `celery.log` - общие логи управления

## Безопасность

1. **Ограничьте доступ** к логам и PID файлам
2. **Используйте отдельного пользователя** для Celery
3. **Настройте firewall** для Redis
4. **Регулярно ротируйте логи**

## Производительность

### Рекомендуемые настройки для разных нагрузок:

**Низкая нагрузка (< 1000 писем/час)**:
- Concurrency: 2-4
- Max tasks per child: 1000
- Prefetch multiplier: 1

**Средняя нагрузка (1000-10000 писем/час)**:
- Concurrency: 4-8
- Max tasks per child: 500
- Prefetch multiplier: 1

**Высокая нагрузка (> 10000 писем/час)**:
- Concurrency: 8-16
- Max tasks per child: 250
- Prefetch multiplier: 1
- Используйте несколько worker процессов

## Обновление

При обновлении кода:

1. **Остановите Celery**:
   ```bash
   ./start_celery_production.sh stop
   ```

2. **Обновите код**

3. **Перезапустите**:
   ```bash
   ./start_celery_production.sh start
   ```

4. **Проверьте статус**:
   ```bash
   ./start_celery_production.sh status
   ``` 