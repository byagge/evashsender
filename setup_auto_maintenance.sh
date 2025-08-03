#!/bin/bash

# VashSender Auto Maintenance Setup
# Настройка автоматического обслуживания системы

PROJECT_DIR="/var/www/vashsender"
LOG_DIR="/var/log/vashsender"

echo "=== VashSender Auto Maintenance Setup ==="

# 1. Делаем скрипты исполняемыми
chmod +x "$PROJECT_DIR/start_celery_production.sh"
chmod +x "$PROJECT_DIR/setup_auto_maintenance.sh"

# 2. Создаем директории для логов
mkdir -p "$LOG_DIR"

# 3. Настраиваем systemd services
echo "Setting up systemd services..."

# Копируем service файлы
cp "$PROJECT_DIR/vashsender-celery-monitor.service" /etc/systemd/system/

# Перезагружаем systemd
systemctl daemon-reload

# Включаем и запускаем monitor service
systemctl enable vashsender-celery-monitor.service
systemctl start vashsender-celery-monitor.service

# 4. Настраиваем cron jobs для дополнительных проверок
echo "Setting up cron jobs..."

# Создаем временный файл для cron
TEMP_CRON=$(mktemp)

# Добавляем существующие cron jobs (если есть)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# Добавляем новые cron jobs
cat >> "$TEMP_CRON" << 'EOF'

# VashSender Auto Maintenance
# Проверка здоровья системы каждые 5 минут
*/5 * * * * cd /var/www/vashsender && source venv/bin/activate && python diagnose_celery.py >> /var/log/vashsender/health_check.log 2>&1

# Очистка старых логов каждые 6 часов
0 */6 * * * find /var/log/vashsender -name "*.log" -mtime +7 -delete

# Полная диагностика каждый час
0 * * * * cd /var/www/vashsender && source venv/bin/activate && python manage.py cleanup_stuck_tasks --force >> /var/log/vashsender/cleanup.log 2>&1

# Проверка дискового пространства каждый час
0 * * * * df -h | grep -E "(/$|/var)" >> /var/log/vashsender/disk_usage.log

# Проверка памяти каждый час
0 * * * * free -h >> /var/log/vashsender/memory_usage.log
EOF

# Устанавливаем cron jobs
crontab "$TEMP_CRON"
rm "$TEMP_CRON"

# 5. Создаем скрипт для уведомлений
cat > "$PROJECT_DIR/send_alert.sh" << 'EOF'
#!/bin/bash

# Скрипт для отправки уведомлений о проблемах
# Можно настроить отправку email или webhook

ALERT_LOG="/var/log/vashsender/alerts.log"
PROJECT_DIR="/var/www/vashsender"

log_alert() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$ALERT_LOG"
}

# Проверяем статус Celery
if ! "$PROJECT_DIR/start_celery_production.sh" health-check > /dev/null 2>&1; then
    log_alert "CRITICAL: Celery health check failed"
fi

# Проверяем зависшие кампании
STUCK_COUNT=$(cd "$PROJECT_DIR" && source venv/bin/activate && python diagnose_celery.py 2>/dev/null | grep -c "зависших кампаний" || echo "0")

if [ "$STUCK_COUNT" -gt 0 ]; then
    log_alert "WARNING: Found $STUCK_COUNT stuck campaigns"
fi

# Проверяем дисковое пространство
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -gt 90 ]; then
    log_alert "CRITICAL: Disk usage is ${DISK_USAGE}%"
fi

# Проверяем память
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')

if [ "$MEMORY_USAGE" -gt 90 ]; then
    log_alert "WARNING: Memory usage is ${MEMORY_USAGE}%"
fi
EOF

chmod +x "$PROJECT_DIR/send_alert.sh"

# Добавляем alert script в cron
(crontab -l 2>/dev/null; echo "*/10 * * * * $PROJECT_DIR/send_alert.sh") | crontab -

# 6. Создаем logrotate конфигурацию
cat > /etc/logrotate.d/vashsender << 'EOF'
/var/log/vashsender/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        systemctl reload vashsender-celery-monitor.service > /dev/null 2>&1 || true
    endscript
}
EOF

# 7. Создаем мониторинг скрипт
cat > "$PROJECT_DIR/monitor_system.py" << 'EOF'
#!/usr/bin/env python3
"""
VashSender System Monitor
Автоматический мониторинг системы и отправка уведомлений
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.insert(0, '/var/www/vashsender')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.production')

import django
django.setup()

from django.core.cache import cache
from apps.campaigns.models import Campaign
from django.utils import timezone

def check_celery_health():
    """Проверка здоровья Celery"""
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            return False, "No active Celery workers"
        
        return True, f"Found {len(stats)} active workers"
    except Exception as e:
        return False, f"Celery health check failed: {e}"

def check_stuck_campaigns():
    """Проверка зависших кампаний"""
    try:
        cutoff_time = timezone.now() - timedelta(minutes=30)
        stuck_campaigns = Campaign.objects.filter(
            status=Campaign.STATUS_SENDING,
            updated_at__lt=cutoff_time
        )
        
        return len(stuck_campaigns), [c.name for c in stuck_campaigns]
    except Exception as e:
        return -1, f"Error checking stuck campaigns: {e}"

def check_redis():
    """Проверка Redis"""
    try:
        cache.set('health_check', 'ok', 60)
        result = cache.get('health_check')
        return result == 'ok', "Redis is working"
    except Exception as e:
        return False, f"Redis check failed: {e}"

def check_disk_space():
    """Проверка дискового пространства"""
    try:
        result = subprocess.run(['df', '/'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                usage = int(parts[4].replace('%', ''))
                return usage < 90, f"Disk usage: {usage}%"
    except Exception as e:
        return False, f"Disk check failed: {e}"
    
    return False, "Unable to check disk space"

def main():
    """Основная функция мониторинга"""
    print(f"[{datetime.now()}] Starting system health check...")
    
    checks = {
        'celery': check_celery_health(),
        'redis': check_redis(),
        'disk': check_disk_space(),
        'stuck_campaigns': check_stuck_campaigns()
    }
    
    # Выводим результаты
    for check_name, (status, message) in checks.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}: {message}")
    
    # Проверяем критические проблемы
    critical_issues = []
    
    if not checks['celery'][0]:
        critical_issues.append("Celery workers not responding")
    
    if not checks['redis'][0]:
        critical_issues.append("Redis connection failed")
    
    if not checks['disk'][0]:
        critical_issues.append("Disk space critical")
    
    if checks['stuck_campaigns'][0] > 0:
        critical_issues.append(f"Found {checks['stuck_campaigns'][0]} stuck campaigns")
    
    if critical_issues:
        print(f"🚨 CRITICAL ISSUES: {', '.join(critical_issues)}")
        return 1
    else:
        print("✅ All systems operational")
        return 0

if __name__ == '__main__':
    exit(main())
EOF

chmod +x "$PROJECT_DIR/monitor_system.py"

# Добавляем system monitor в cron
(crontab -l 2>/dev/null; echo "*/5 * * * * $PROJECT_DIR/monitor_system.py >> /var/log/vashsender/system_monitor.log 2>&1") | crontab -

echo "=== Setup Complete ==="
echo
echo "Services configured:"
echo "✅ vashsender-celery-monitor.service (enabled and started)"
echo "✅ Cron jobs for health checks"
echo "✅ Log rotation configuration"
echo "✅ System monitoring script"
echo
echo "Monitoring commands:"
echo "  systemctl status vashsender-celery-monitor"
echo "  tail -f /var/log/vashsender/system_monitor.log"
echo "  tail -f /var/log/vashsender/alerts.log"
echo "  $PROJECT_DIR/start_celery_production.sh status"
echo
echo "Auto-maintenance is now active!" 