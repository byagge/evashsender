#!/usr/bin/env python3
"""
Скрипт для настройки локального Postfix для отправки писем
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Выполнить команду и показать результат"""
    print(f"\n🔧 {description}")
    print(f"Команда: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Успешно: {result.stdout}")
        else:
            print(f"❌ Ошибка: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False

def main():
    print("🚀 НАСТРОЙКА ЛОКАЛЬНОГО SMTP ДЛЯ ОТПРАВКИ ПИСЕМ")
    print("=" * 60)
    
    # Проверяем, что мы root
    if os.geteuid() != 0:
        print("❌ Этот скрипт должен выполняться от имени root")
        sys.exit(1)
    
    print("\n📋 Текущие настройки Postfix:")
    run_command("postconf -n", "Показать текущие настройки")
    
    print("\n🔍 Проверка статуса Postfix:")
    run_command("systemctl status postfix", "Статус Postfix")
    
    print("\n⚙️ Настройка Postfix для отправки писем:")
    
    # Настройка для отправки писем во внешние домены
    configs = [
        # Разрешаем отправку из локальных сетей
        "postconf -e 'mynetworks = 127.0.0.0/8 [::1]/128 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16'",
        
        # Настройка для отправки писем
        "postconf -e 'relayhost ='",
        "postconf -e 'smtp_tls_security_level = may'",
        "postconf -e 'smtp_tls_session_cache_database = btree:\${data_directory}/smtp_scache'",
        
        # Настройка для приема писем
        "postconf -e 'smtpd_relay_restrictions = permit_mynetworks, permit_sasl_authenticated, defer_unauth_destination'",
        "postconf -e 'smtpd_recipient_restrictions = permit_mynetworks, permit_sasl_authenticated, reject_unauth_destination'",
        
        # Настройка для аутентификации
        "postconf -e 'smtpd_sasl_auth_enable = yes'",
        "postconf -e 'smtpd_sasl_local_domain = \$myhostname'",
        "postconf -e 'smtpd_sasl_security_options = noanonymous'",
        
        # Настройка TLS
        "postconf -e 'smtpd_tls_security_level = may'",
        "postconf -e 'smtpd_tls_cert_file = /etc/ssl/certs/ssl-cert-snakeoil.pem'",
        "postconf -e 'smtpd_tls_key_file = /etc/ssl/private/ssl-cert-snakeoil.key'",
        
        # Настройка для больших писем
        "postconf -e 'message_size_limit = 10485760'",  # 10MB
        "postconf -e 'mailbox_size_limit = 0'",
        
        # Настройка для отладки
        "postconf -e 'debug_peer_level = 2'",
        "postconf -e 'debug_peer_list = 127.0.0.1'",
    ]
    
    for config in configs:
        if not run_command(config, f"Применение настройки: {config}"):
            print(f"⚠️ Предупреждение: не удалось применить {config}")
    
    print("\n🔄 Перезапуск Postfix:")
    run_command("systemctl restart postfix", "Перезапуск Postfix")
    
    print("\n✅ Проверка статуса после настройки:")
    run_command("systemctl status postfix", "Статус Postfix после настройки")
    
    print("\n📧 Тестирование отправки письма:")
    test_email = """
From: noreply@vashsender.ru
To: test@example.com
Subject: Test email from VashSender
Content-Type: text/plain; charset=utf-8

Это тестовое письмо от VashSender.
Время отправки: $(date)
"""
    
    # Сохраняем тестовое письмо во временный файл
    with open('/tmp/test_email.txt', 'w', encoding='utf-8') as f:
        f.write(test_email)
    
    run_command("cat /tmp/test_email.txt | sendmail -t", "Отправка тестового письма")
    
    print("\n📋 Финальные настройки Postfix:")
    run_command("postconf -n", "Показать финальные настройки")
    
    print("\n🎯 РЕКОМЕНДАЦИИ:")
    print("1. Проверьте логи Postfix: tail -f /var/log/mail.log")
    print("2. Если письма не доходят, проверьте DNS записи домена")
    print("3. Убедитесь, что IP сервера не заблокирован провайдерами")
    print("4. Рассмотрите использование внешнего SMTP для надежности")
    
    print("\n✅ Настройка завершена!")

if __name__ == "__main__":
    main() 