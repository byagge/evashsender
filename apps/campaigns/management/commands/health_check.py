from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
import redis
import smtplib
import time


class Command(BaseCommand):
    help = 'Проверка здоровья системы отправки писем'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Полная проверка всех компонентов',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 Проверка здоровья системы VashSender...')
        
        checks = []
        
        # Проверка базы данных
        checks.append(self.check_database())
        
        # Проверка Redis
        checks.append(self.check_redis())
        
        # Проверка Celery
        checks.append(self.check_celery())
        
        if options['full']:
            # Проверка SMTP
            checks.append(self.check_smtp())
            
            # Проверка кэша
            checks.append(self.check_cache())
            
            # Проверка статических файлов
            checks.append(self.check_static_files())
        
        # Выводим результаты
        self.stdout.write('\n📊 Результаты проверки:')
        self.stdout.write('=' * 50)
        
        all_passed = True
        for check in checks:
            status = '✅' if check['status'] else '❌'
            self.stdout.write(f"{status} {check['name']}: {check['message']}")
            if not check['status']:
                all_passed = False
        
        self.stdout.write('=' * 50)
        
        if all_passed:
            self.stdout.write(
                self.style.SUCCESS('🎉 Все проверки пройдены! Система готова к работе.')
            )
        else:
            self.stdout.write(
                self.style.ERROR('⚠️  Обнаружены проблемы. Проверьте логи и настройки.')
            )
    
    def check_database(self):
        """Проверка подключения к базе данных"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return {
                'name': 'База данных',
                'status': True,
                'message': 'Подключение активно'
            }
        except Exception as e:
            return {
                'name': 'База данных',
                'status': False,
                'message': f'Ошибка подключения: {str(e)}'
            }
    
    def check_redis(self):
        """Проверка подключения к Redis"""
        try:
            r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
            r.ping()
            return {
                'name': 'Redis',
                'status': True,
                'message': 'Подключение активно'
            }
        except Exception as e:
            return {
                'name': 'Redis',
                'status': False,
                'message': f'Ошибка подключения: {str(e)}'
            }
    
    def check_celery(self):
        """Проверка Celery"""
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                active_workers = len(stats)
                return {
                    'name': 'Celery',
                    'status': True,
                    'message': f'{active_workers} активных worker процессов'
                }
            else:
                return {
                    'name': 'Celery',
                    'status': False,
                    'message': 'Нет активных worker процессов'
                }
        except Exception as e:
            return {
                'name': 'Celery',
                'status': False,
                'message': f'Ошибка проверки: {str(e)}'
            }
    
    def check_smtp(self):
        """Проверка SMTP сервера"""
        try:
            smtp = smtplib.SMTP(
                settings.EMAIL_HOST,
                settings.EMAIL_PORT,
                timeout=10
            )
            
            if settings.EMAIL_USE_TLS:
                smtp.starttls()
            
            if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
                smtp.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            
            smtp.quit()
            
            return {
                'name': 'SMTP',
                'status': True,
                'message': f'{settings.EMAIL_HOST}:{settings.EMAIL_PORT} доступен'
            }
        except Exception as e:
            return {
                'name': 'SMTP',
                'status': False,
                'message': f'Ошибка подключения: {str(e)}'
            }
    
    def check_cache(self):
        """Проверка кэша"""
        try:
            cache.set('health_check', 'ok', 60)
            value = cache.get('health_check')
            
            if value == 'ok':
                return {
                    'name': 'Кэш',
                    'status': True,
                    'message': 'Работает корректно'
                }
            else:
                return {
                    'name': 'Кэш',
                    'status': False,
                    'message': 'Ошибка записи/чтения'
                }
        except Exception as e:
            return {
                'name': 'Кэш',
                'status': False,
                'message': f'Ошибка: {str(e)}'
            }
    
    def check_static_files(self):
        """Проверка статических файлов"""
        try:
            import os
            static_root = getattr(settings, 'STATIC_ROOT', None)
            
            if static_root and os.path.exists(static_root):
                return {
                    'name': 'Статические файлы',
                    'status': True,
                    'message': f'Директория {static_root} существует'
                }
            else:
                return {
                    'name': 'Статические файлы',
                    'status': False,
                    'message': 'Директория не найдена'
                }
        except Exception as e:
            return {
                'name': 'Статические файлы',
                'status': False,
                'message': f'Ошибка: {str(e)}'
            } 