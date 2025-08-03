#!/usr/bin/env python
"""
Скрипт для настройки DKIM и улучшения доставляемости писем в Mail.ru
"""

import os
import sys
import django
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
django.setup()

from django.conf import settings
from apps.emails.models import Domain, SenderEmail
from apps.emails.dkim_service import DKIMService
import dns.resolver
import dns.reversename
import dns.resolver


def check_dns_records():
    """Проверяет DNS записи для улучшения доставляемости"""
    print("🔍 Проверка DNS записей...")
    
    # Проверяем rDNS
    print("\n1. Проверка rDNS (обратный DNS):")
    try:
        ip = "146.185.196.123"
        reverse_name = dns.reversename.from_address(ip)
        answers = dns.resolver.resolve(reverse_name, "PTR")
        ptr_record = str(answers[0])
        print(f"   IP {ip} → {ptr_record}")
        
        if "vashsender.ru" in ptr_record:
            print("   ✅ rDNS настроен правильно")
        else:
            print("   ❌ rDNS НЕ настроен правильно!")
            print("   Нужно: 146.185.196.123 → mail.vashsender.ru")
    except Exception as e:
        print(f"   ❌ Ошибка проверки rDNS: {e}")
    
    # Проверяем SPF
    print("\n2. Проверка SPF записи:")
    try:
        answers = dns.resolver.resolve("vashsender.ru", "TXT")
        spf_found = False
        for rdata in answers:
            txt = ''.join(rdata.strings).decode('utf-8')
            if txt.startswith('v=spf1'):
                print(f"   SPF: {txt}")
                if "146.185.196.123" in txt:
                    print("   ✅ SPF содержит правильный IP")
                    spf_found = True
                else:
                    print("   ❌ SPF НЕ содержит правильный IP!")
        if not spf_found:
            print("   ❌ SPF запись не найдена!")
    except Exception as e:
        print(f"   ❌ Ошибка проверки SPF: {e}")
    
    # Проверяем DKIM
    print("\n3. Проверка DKIM записей:")
    try:
        selector = getattr(settings, 'DKIM_SELECTOR', 'ep1')
        dkim_name = f"{selector}._domainkey.vashsender.ru"
        answers = dns.resolver.resolve(dkim_name, "TXT")
        for rdata in answers:
            txt = ''.join(rdata.strings).decode('utf-8')
            if txt.startswith('v=DKIM1'):
                print(f"   DKIM ({selector}): {txt[:100]}...")
                print("   ✅ DKIM запись найдена")
                break
        else:
            print(f"   ❌ DKIM запись для селектора {selector} не найдена!")
    except Exception as e:
        print(f"   ❌ Ошибка проверки DKIM: {e}")
    
    # Проверяем DMARC
    print("\n4. Проверка DMARC записи:")
    try:
        answers = dns.resolver.resolve("_dmarc.vashsender.ru", "TXT")
        dmarc_found = False
        for rdata in answers:
            txt = ''.join(rdata.strings).decode('utf-8')
            if txt.startswith('v=DMARC1'):
                print(f"   DMARC: {txt}")
                dmarc_found = True
                break
        if not dmarc_found:
            print("   ❌ DMARC запись не найдена!")
            print("   Рекомендуется добавить: v=DMARC1; p=quarantine; rua=mailto:dmarc@vashsender.ru")
    except Exception as e:
        print(f"   ❌ Ошибка проверки DMARC: {e}")


def setup_dkim_for_domains():
    """Настраивает DKIM для всех доменов в системе"""
    print("\n🔧 Настройка DKIM для доменов...")
    
    service = DKIMService()
    
    # Получаем все домены
    domains = Domain.objects.all()
    print(f"Найдено доменов: {domains.count()}")
    
    for domain in domains:
        print(f"\nОбработка домена: {domain.domain_name}")
        
        # Проверяем, есть ли уже DKIM ключи
        if domain.public_key and domain.private_key_path:
            print(f"   DKIM ключи уже существуют")
            
            # Проверяем, что файл приватного ключа существует
            if os.path.exists(domain.private_key_path):
                print(f"   ✅ Приватный ключ найден: {domain.private_key_path}")
            else:
                print(f"   ❌ Приватный ключ не найден: {domain.private_key_path}")
                print(f"   Генерируем новые ключи...")
                if domain.generate_dkim_keys():
                    print(f"   ✅ Новые DKIM ключи сгенерированы")
                else:
                    print(f"   ❌ Ошибка генерации DKIM ключей")
        else:
            print(f"   DKIM ключи отсутствуют, генерируем...")
            if domain.generate_dkim_keys():
                print(f"   ✅ DKIM ключи сгенерированы")
            else:
                print(f"   ❌ Ошибка генерации DKIM ключей")
        
        # Показываем DNS запись для добавления
        if domain.public_key:
            print(f"   DNS запись для добавления:")
            print(f"   {domain.dkim_dns_record}")


def check_email_headers():
    """Проверяет заголовки писем для улучшения доставляемости"""
    print("\n📧 Проверка заголовков писем...")
    
    # Получаем все email адреса отправителей
    sender_emails = SenderEmail.objects.all()
    print(f"Найдено email адресов отправителей: {sender_emails.count()}")
    
    for sender in sender_emails:
        print(f"\nEmail: {sender.email}")
        print(f"   Домен: {sender.domain.domain_name}")
        print(f"   Имя отправителя: '{sender.sender_name}'")
        print(f"   Reply-To: {sender.reply_to}")
        
        # Проверяем корректность email
        if '@' in sender.email and sender.email.count('@') == 1:
            print(f"   ✅ Email корректный")
        else:
            print(f"   ❌ Email некорректный!")
        
        # Проверяем домен
        domain_part = sender.email.split('@')[1] if '@' in sender.email else ''
        if domain_part == sender.domain.domain_name:
            print(f"   ✅ Домен соответствует")
        else:
            print(f"   ❌ Домен НЕ соответствует!")


def generate_dns_recommendations():
    """Генерирует рекомендации по настройке DNS"""
    print("\n📋 Рекомендации по настройке DNS:")
    
    print("\n1. SPF запись (добавить в DNS vashsender.ru):")
    print("   v=spf1 ip4:146.185.196.123 ~all")
    
    print("\n2. DMARC запись (добавить в DNS _dmarc.vashsender.ru):")
    print("   v=DMARC1; p=quarantine; rua=mailto:dmarc@vashsender.ru; ruf=mailto:dmarc@vashsender.ru")
    
    print("\n3. rDNS запись (настроить у хостинг-провайдера):")
    print("   146.185.196.123 → mail.vashsender.ru")
    
    print("\n4. A запись для mail.vashsender.ru:")
    print("   mail.vashsender.ru → 146.185.196.123")
    
    # Показываем DKIM записи для всех доменов
    domains = Domain.objects.all()
    if domains.exists():
        print("\n5. DKIM записи:")
        for domain in domains:
            if domain.public_key:
                selector = domain.dkim_selector
                print(f"   {selector}._domainkey.{domain.domain_name} (TXT):")
                print(f"   {domain.dkim_dns_record}")


def main():
    """Основная функция"""
    print("🚀 Настройка доставляемости писем для Mail.ru")
    print("=" * 50)
    
    # Проверяем DNS записи
    check_dns_records()
    
    # Настраиваем DKIM
    setup_dkim_for_domains()
    
    # Проверяем заголовки писем
    check_email_headers()
    
    # Генерируем рекомендации
    generate_dns_recommendations()
    
    print("\n" + "=" * 50)
    print("✅ Проверка завершена!")
    print("\n📝 Следующие шаги:")
    print("1. Настройте DNS записи согласно рекомендациям выше")
    print("2. Установите библиотеку dkimpy: pip install dkimpy")
    print("3. Перезапустите Celery workers")
    print("4. Подождите 24-48 часа для распространения DNS изменений")
    print("5. Протестируйте отправку писем")


if __name__ == "__main__":
    main() 