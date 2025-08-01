from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys
import os


class Command(BaseCommand):
    help = 'Запускает Celery worker для обработки email задач'

    def add_arguments(self, parser):
        parser.add_argument(
            '--concurrency',
            type=int,
            default=4,
            help='Количество worker процессов (по умолчанию: 4)'
        )
        parser.add_argument(
            '--queues',
            type=str,
            default='email,campaigns,default',
            help='Очереди для обработки (по умолчанию: email,campaigns,default)'
        )
        parser.add_argument(
            '--loglevel',
            type=str,
            default='info',
            choices=['debug', 'info', 'warning', 'error'],
            help='Уровень логирования (по умолчанию: info)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Запуск Celery worker для VashSender...')
        
        # Формируем команду для запуска Celery worker
        cmd = [
            'celery',
            '-A', 'core',
            'worker',
            '--loglevel=' + options['loglevel'],
            '--concurrency=' + str(options['concurrency']),
            '--queues=' + options['queues'],
            '--hostname=worker@%h',
            '--max-tasks-per-child=1000',
            '--prefetch-multiplier=1',
            '--without-gossip',
            '--without-mingle',
            '--without-heartbeat'
        ]
        
        self.stdout.write(f'Команда: {" ".join(cmd)}')
        self.stdout.write('Запуск worker... (Ctrl+C для остановки)')
        
        try:
            # Запускаем Celery worker
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Worker остановлен пользователем'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка запуска worker: {e}')
            )
            sys.exit(1)
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR('Celery не найден. Установите: pip install celery')
            )
            sys.exit(1) 