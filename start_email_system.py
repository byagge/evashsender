#!/usr/bin/env python3
"""
Скрипт для запуска системы отправки писем VashSender
Запускает все необходимые компоненты: Redis, Celery Worker, Flower
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path

class EmailSystemManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def check_redis(self):
        """Проверяет, запущен ли Redis"""
        try:
            result = subprocess.run(['redis-cli', 'ping'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout.strip() == 'PONG'
        except:
            return False
    
    def start_redis(self):
        """Запускает Redis если не запущен"""
        if self.check_redis():
            print("✅ Redis уже запущен")
            return
        
        print("🚀 Запуск Redis...")
        try:
            # Пытаемся запустить Redis
            process = subprocess.Popen(['redis-server'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE)
            time.sleep(2)
            
            if self.check_redis():
                print("✅ Redis успешно запущен")
                self.processes.append(('redis-server', process))
            else:
                print("❌ Не удалось запустить Redis")
                print("Установите Redis: sudo apt install redis-server")
                sys.exit(1)
                
        except FileNotFoundError:
            print("❌ Redis не найден")
            print("Установите Redis: sudo apt install redis-server")
            sys.exit(1)
    
    def start_celery_worker(self):
        """Запускает Celery Worker"""
        print("🚀 Запуск Celery Worker...")
        try:
            process = subprocess.Popen([
                'python', 'manage.py', 'start_celery_worker',
                '--concurrency=8',
                '--queues=email,campaigns,default',
                '--loglevel=info'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(('celery-worker', process))
            print("✅ Celery Worker запущен")
            
        except Exception as e:
            print(f"❌ Ошибка запуска Celery Worker: {e}")
            sys.exit(1)
    
    def start_flower(self):
        """Запускает Flower для мониторинга"""
        print("🚀 Запуск Flower (мониторинг)...")
        try:
            process = subprocess.Popen([
                'python', 'manage.py', 'start_flower',
                '--port=5555',
                '--host=localhost'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(('flower', process))
            print("✅ Flower запущен (http://localhost:5555)")
            
        except Exception as e:
            print(f"❌ Ошибка запуска Flower: {e}")
    
    def start_django(self):
        """Запускает Django сервер"""
        print("🚀 Запуск Django сервера...")
        try:
            process = subprocess.Popen([
                'python', 'manage.py', 'runserver', '0.0.0.0:8000'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(('django', process))
            print("✅ Django сервер запущен (http://localhost:8000)")
            
        except Exception as e:
            print(f"❌ Ошибка запуска Django: {e}")
            sys.exit(1)
    
    def monitor_processes(self):
        """Мониторит процессы и перезапускает упавшие"""
        while self.running:
            for name, process in self.processes[:]:
                if process.poll() is not None:
                    print(f"⚠️  Процесс {name} завершился, перезапуск...")
                    self.processes.remove((name, process))
                    
                    if name == 'celery-worker':
                        self.start_celery_worker()
                    elif name == 'flower':
                        self.start_flower()
                    elif name == 'django':
                        self.start_django()
            
            time.sleep(5)
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        print("\n🛑 Получен сигнал завершения, останавливаю процессы...")
        self.running = False
        
        for name, process in self.processes:
            print(f"Остановка {name}...")
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        
        print("✅ Все процессы остановлены")
        sys.exit(0)
    
    def run(self):
        """Основной метод запуска системы"""
        print("🚀 Запуск системы отправки писем VashSender")
        print("=" * 50)
        
        # Регистрируем обработчик сигналов
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Запускаем компоненты
        self.start_redis()
        self.start_celery_worker()
        self.start_flower()
        self.start_django()
        
        print("\n" + "=" * 50)
        print("🎉 Система запущена!")
        print("📊 Мониторинг: http://localhost:5555")
        print("🌐 Веб-интерфейс: http://localhost:8000")
        print("📧 Готов к отправке 10,000+ писем!")
        print("=" * 50)
        print("Нажмите Ctrl+C для остановки")
        
        # Запускаем мониторинг в отдельном потоке
        monitor_thread = threading.Thread(target=self.monitor_processes)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Ждем завершения
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.signal_handler(signal.SIGINT, None)

def main():
    # Проверяем, что мы в правильной директории
    if not Path('manage.py').exists():
        print("❌ Файл manage.py не найден")
        print("Запустите скрипт из корневой директории проекта")
        sys.exit(1)
    
    # Проверяем зависимости
    try:
        import celery
        import redis
        import django
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("Установите зависимости: pip install -r requirements.txt")
        sys.exit(1)
    
    # Запускаем систему
    manager = EmailSystemManager()
    manager.run()

if __name__ == '__main__':
    main() 