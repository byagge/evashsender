# emails/utils.py
import dns.resolver
import re

def has_spf(domain_name):
    """
    Проверяет наличие валидной SPF записи у домена
    """
    try:
        answers = dns.resolver.resolve(domain_name, 'TXT')
        for r in answers:
            txt = b''.join(r.strings).decode('utf-8', errors='ignore').strip('"')
            print(f"Checking TXT record: {txt}")  # Отладка
            
            # Проверяем, что это SPF запись
            if txt.lower().startswith('v=spf1'):
                print(f"SPF record found: {txt}")  # Отладка
                return True
    except Exception as e:
        print(f"Error checking SPF for {domain_name}: {e}")  # Отладка
        pass
    return False

def validate_spf_record(spf_record):
    """
    Валидирует SPF запись на соответствие RFC 7208
    """
    if not spf_record:
        return False
    
    spf = spf_record.lower().strip()
    
    # Должна начинаться с v=spf1
    if not spf.startswith('v=spf1'):
        return False
    
    # Проверяем базовый синтаксис
    parts = spf.split()
    if len(parts) < 1:
        return False
    
    # Проверяем механизмы
    valid_mechanisms = ['all', 'include:', 'a', 'mx', 'ip4:', 'ip6:', 'exists:', 'ptr']
    valid_qualifiers = ['+', '-', '~', '?']
    
    for part in parts[1:]:  # Пропускаем v=spf1
        if not part:
            continue
            
        # Проверяем квалификатор
        if part[0] in valid_qualifiers:
            part = part[1:]
        
        # Проверяем механизм
        valid_mechanism = False
        for mechanism in valid_mechanisms:
            if part.startswith(mechanism):
                valid_mechanism = True
                break
        
        if not valid_mechanism:
            print(f"Invalid SPF mechanism: {part}")
            return False
    
    return True

def has_dkim(domain_name, selector='ep1'):
    """
    Проверяет наличие DKIM записи
    """
    try:
        # например для ep1._domainkey.domain.com
        name = f'{selector}._domainkey.{domain_name}'
        answers = dns.resolver.resolve(name, 'TXT')
        for r in answers:
            txt = b''.join(r.strings).decode('utf-8', errors='ignore').strip('"')
            print(f"DKIM record for {name}: {txt}")  # Отладка
            if txt.startswith('v=DKIM1'):
                print(f"Valid DKIM record found: {txt}")  # Отладка
                return True
        return False
    except Exception as e:
        print(f"Error checking DKIM for {domain_name}: {e}")  # Отладка
        return False
