from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys
import os


class Command(BaseCommand):
    help = 'Запускает Flower для мониторинга Celery задач'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=5555,
            help='Порт для Flower (по умолчанию: 5555)'
        )
        parser.add_argument(
            '--host',
            type=str,
            default='localhost',
            help='Хост для Flower (по умолчанию: localhost)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Запуск Flower для мониторинга VashSender...')
        
        # Формируем команду для запуска Flower
        cmd = [
            'celery',
            '-A', 'core',
            'flower',
            '--port=' + str(options['port']),
            '--host=' + options['host'],
            '--broker=redis://localhost:6379/0',
            '--result-backend=redis://localhost:6379/0',
            '--auto-refresh=True',
            '--enable-events=True',
            '--persistent=True'
        ]
        
        self.stdout.write(f'Команда: {" ".join(cmd)}')
        self.stdout.write(f'Flower будет доступен по адресу: http://{options["host"]}:{options["port"]}')
        self.stdout.write('Запуск Flower... (Ctrl+C для остановки)')
        
        try:
            # Запускаем Flower
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Flower остановлен пользователем'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка запуска Flower: {e}')
            )
            sys.exit(1)
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR('Flower не найден. Установите: pip install flower')
            )
            sys.exit(1) 