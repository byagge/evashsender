#!/bin/bash

# Скрипт для запуска Celery в продакшене
# Включает worker, beat scheduler и мониторинг

set -e

# Настройки
PROJECT_DIR="/var/www/vashsender"
LOG_DIR="/var/log/vashsender"
PID_DIR="/var/run/vashsender"
CELERY_APP="core"

# Создаем директории если не существуют
mkdir -p $LOG_DIR
mkdir -p $PID_DIR

# Функция для логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_DIR/celery.log
}

# Функция для остановки процессов
stop_celery() {
    log "Останавливаем Celery процессы..."
    
    # Останавливаем worker
    if [ -f $PID_DIR/celery_worker.pid ]; then
        kill -TERM $(cat $PID_DIR/celery_worker.pid) 2>/dev/null || true
        rm -f $PID_DIR/celery_worker.pid
    fi
    
    # Останавливаем beat
    if [ -f $PID_DIR/celery_beat.pid ]; then
        kill -TERM $(cat $PID_DIR/celery_beat.pid) 2>/dev/null || true
        rm -f $PID_DIR/celery_beat.pid
    fi
    
    # Ждем завершения процессов
    sleep 5
    
    # Принудительно завершаем если нужно
    pkill -f "celery.*worker" 2>/dev/null || true
    pkill -f "celery.*beat" 2>/dev/null || true
    
    log "Celery процессы остановлены"
}

# Функция для запуска worker
start_worker() {
    log "Запускаем Celery worker..."
    
    cd $PROJECT_DIR
    
    celery -A $CELERY_APP worker \
        --loglevel=info \
        --concurrency=4 \
        --max-tasks-per-child=1000 \
        --prefetch-multiplier=1 \
        --queues=campaigns,email,default \
        --pidfile=$PID_DIR/celery_worker.pid \
        --logfile=$LOG_DIR/celery_worker.log \
        --detach
}

# Функция для запуска beat scheduler
start_beat() {
    log "Запускаем Celery beat scheduler..."
    
    cd $PROJECT_DIR
    
    celery -A $CELERY_APP beat \
        --loglevel=info \
        --pidfile=$PID_DIR/celery_beat.pid \
        --logfile=$LOG_DIR/celery_beat.log \
        --detach \
        --schedule=/tmp/celerybeat-schedule
}

# Функция для мониторинга
monitor_celery() {
    log "Запускаем мониторинг Celery..."
    
    while true; do
        # Проверяем worker
        if [ ! -f $PID_DIR/celery_worker.pid ] || ! kill -0 $(cat $PID_DIR/celery_worker.pid) 2>/dev/null; then
            log "Worker не работает, перезапускаем..."
            start_worker
        fi
        
        # Проверяем beat
        if [ ! -f $PID_DIR/celery_beat.pid ] || ! kill -0 $(cat $PID_DIR/celery_beat.pid) 2>/dev/null; then
            log "Beat scheduler не работает, перезапускаем..."
            start_beat
        fi
        
        # Проверяем каждые 30 секунд
        sleep 30
    done
}

# Обработка сигналов
trap stop_celery SIGTERM SIGINT

# Основная логика
case "$1" in
    start)
        log "Запуск Celery в продакшене..."
        stop_celery
        start_worker
        start_beat
        log "Celery запущен"
        ;;
    stop)
        log "Остановка Celery..."
        stop_celery
        log "Celery остановлен"
        ;;
    restart)
        log "Перезапуск Celery..."
        stop_celery
        sleep 2
        start_worker
        start_beat
        log "Celery перезапущен"
        ;;
    monitor)
        log "Запуск мониторинга..."
        monitor_celery
        ;;
    status)
        echo "=== Статус Celery ==="
        echo "Worker PID: $(cat $PID_DIR/celery_worker.pid 2>/dev/null || echo 'Не запущен')"
        echo "Beat PID: $(cat $PID_DIR/celery_beat.pid 2>/dev/null || echo 'Не запущен')"
        echo "Логи: $LOG_DIR/"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|monitor|status}"
        exit 1
        ;;
esac

exit 0 