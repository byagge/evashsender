from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys
import os


class Command(BaseCommand):
    help = 'Запускает Celery beat для периодических задач'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            type=str,
            default='info',
            choices=['debug', 'info', 'warning', 'error'],
            help='Уровень логирования (по умолчанию: info)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Запуск Celery beat для VashSender...')
        
        # Формируем команду для запуска Celery beat
        cmd = [
            'celery',
            '-A', 'core',
            'beat',
            '--loglevel=' + options['loglevel'],
            '--scheduler=django_celery_beat.schedulers:DatabaseScheduler',
            '--max-interval=300'  # Максимальный интервал 5 минут
        ]
        
        self.stdout.write(f'Команда: {" ".join(cmd)}')
        self.stdout.write('Запуск beat... (Ctrl+C для остановки)')
        
        try:
            # Запускаем Celery beat
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Beat остановлен пользователем'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка запуска beat: {e}')
            )
            sys.exit(1)
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR('Celery не найден. Установите: pip install celery')
            )
            sys.exit(1) 