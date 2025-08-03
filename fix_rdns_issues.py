#!/usr/bin/env python3
"""
Скрипт для диагностики и исправления проблем с доставляемостью писем
"""

import os
import sys
import socket
import dns.resolver
import dns.reversename
from django.conf import settings
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.local')
django.setup()

def check_rdns(ip_address):
    """Проверка обратного DNS для IP адреса"""
    try:
        # Получаем обратный DNS
        reverse_name = dns.reversename.from_address(ip_address)
        answers = dns.resolver.resolve(reverse_name, "PTR")
        rdns_name = str(answers[0])
        print(f"✅ rDNS для {ip_address}: {rdns_name}")
        return rdns_name
    except Exception as e:
        print(f"❌ rDNS для {ip_address}: ОШИБКА - {e}")
        return None

def check_forward_dns(hostname):
    """Проверка прямого DNS для хоста"""
    try:
        answers = dns.resolver.resolve(hostname, "A")
        ip_addresses = [str(answer) for answer in answers]
        print(f"✅ Прямой DNS для {hostname}: {ip_addresses}")
        return ip_addresses
    except Exception as e:
        print(f"❌ Прямой DNS для {hostname}: ОШИБКА - {e}")
        return []

def check_spf_record(domain):
    """Проверка SPF записи для домена"""
    try:
        answers = dns.resolver.resolve(domain, "TXT")
        spf_records = [str(answer) for answer in answers if 'v=spf1' in str(answer)]
        if spf_records:
            print(f"✅ SPF для {domain}: {spf_records}")
            return spf_records
        else:
            print(f"⚠️  SPF для {domain}: НЕ НАЙДЕН")
            return []
    except Exception as e:
        print(f"❌ SPF для {domain}: ОШИБКА - {e}")
        return []

def check_dkim_record(domain, selector='ep1'):
    """Проверка DKIM записи для домена"""
    try:
        dkim_domain = f"{selector}._domainkey.{domain}"
        answers = dns.resolver.resolve(dkim_domain, "TXT")
        dkim_records = [str(answer) for answer in answers if 'v=DKIM1' in str(answer)]
        if dkim_records:
            print(f"✅ DKIM для {domain}: {dkim_records}")
            return dkim_records
        else:
            print(f"⚠️  DKIM для {domain}: НЕ НАЙДЕН")
            return []
    except Exception as e:
        print(f"❌ DKIM для {domain}: ОШИБКА - {e}")
        return []

def check_mx_record(domain):
    """Проверка MX записи для домена"""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        mx_records = [(str(answer.exchange), answer.preference) for answer in answers]
        print(f"✅ MX для {domain}: {mx_records}")
        return mx_records
    except Exception as e:
        print(f"❌ MX для {domain}: ОШИБКА - {e}")
        return []

def get_server_ip():
    """Получение IP адреса сервера"""
    try:
        # Получаем внешний IP
        import requests
        response = requests.get('https://api.ipify.org', timeout=5)
        external_ip = response.text
        print(f"🌐 Внешний IP сервера: {external_ip}")
        return external_ip
    except:
        # Fallback - получаем локальный IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"🏠 Локальный IP сервера: {local_ip}")
        return local_ip

def main():
    print("🔍 Диагностика проблем с доставляемостью писем")
    print("=" * 60)
    
    # Получаем IP сервера
    server_ip = get_server_ip()
    
    # Проверяем rDNS
    print("\n📋 Проверка rDNS:")
    rdns_name = check_rdns(server_ip)
    
    # Проверяем прямой DNS для mail.vashsender.ru
    print("\n📋 Проверка DNS для mail.vashsender.ru:")
    mail_ips = check_forward_dns('mail.vashsender.ru')
    
    # Проверяем домен vashsender.ru
    print("\n📋 Проверка домена vashsender.ru:")
    check_spf_record('vashsender.ru')
    check_dkim_record('vashsender.ru')
    check_mx_record('vashsender.ru')
    
    # Проверяем SMTP настройки
    print("\n📋 Проверка SMTP настроек:")
    print(f"SMTP Host: {settings.EMAIL_HOST}")
    print(f"SMTP Port: {settings.EMAIL_PORT}")
    print(f"SMTP TLS: {settings.EMAIL_USE_TLS}")
    print(f"SMTP SSL: {settings.EMAIL_USE_SSL}")
    print(f"Default From: {settings.DEFAULT_FROM_EMAIL}")
    
    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ:")
    
    if not rdns_name:
        print("❌ ПРОБЛЕМА: Отсутствует rDNS для IP сервера")
        print("   РЕШЕНИЕ: Настройте PTR запись для IP в DNS провайдере")
        print(f"   Нужно: {server_ip} -> mail.vashsender.ru")
    
    if server_ip not in mail_ips:
        print("❌ ПРОБЛЕМА: IP сервера не соответствует mail.vashsender.ru")
        print("   РЕШЕНИЕ: Обновите A запись для mail.vashsender.ru")
        print(f"   Нужно: mail.vashsender.ru -> {server_ip}")
    
    # Проверяем соответствие rDNS и HELO
    if rdns_name and 'mail.vashsender.ru' not in rdns_name:
        print("❌ ПРОБЛЕМА: rDNS не соответствует HELO")
        print("   РЕШЕНИЕ: Настройте rDNS чтобы он содержал mail.vashsender.ru")
        print(f"   Текущий rDNS: {rdns_name}")
        print("   Ожидаемый: mail.vashsender.ru")
    
    print("\n✅ Проверка завершена!")

if __name__ == "__main__":
    main() 