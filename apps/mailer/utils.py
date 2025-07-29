import re
import dns.resolver
import requests
import socket
from .models import Contact

# Более строгое регулярное выражение для email
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$')

# Дополнительные проверки
MAX_EMAIL_LENGTH = 254  # RFC 5321
MAX_LOCAL_LENGTH = 64   # RFC 5321
MAX_DOMAIN_LENGTH = 253 # RFC 5321

# Кэш для загруженных disposable-доменов
DISPOSABLE_DOMAINS = None

# Список зарезервированных доменов верхнего уровня
RESERVED_TLDS = {
    'test', 'example', 'invalid', 'localhost', 'local', 'internal', 'intranet',
    'private', 'corp', 'home', 'lan', 'workgroup', 'dev', 'development'
}

# Список зарезервированных доменов второго уровня
RESERVED_SLDS = {
    'example.com', 'example.org', 'example.net', 'test.com', 'test.org',
    'invalid.com', 'localhost.com', 'dummy.com', 'fake.com', 'spam.com'
}

def load_disposable_domains():
    """
    Загружает список disposable-доменов только один раз при первом вызове.
    """
    global DISPOSABLE_DOMAINS
    if DISPOSABLE_DOMAINS is not None:
        return DISPOSABLE_DOMAINS

    url = "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            DISPOSABLE_DOMAINS = set(
                line.strip().lower()
                for line in response.text.splitlines()
                if line.strip() and not line.startswith('#')
            )
            print(f"{len(DISPOSABLE_DOMAINS)} disposable доменов загружено.")
        else:
            print("Не удалось загрузить список disposable-доменов.")
            DISPOSABLE_DOMAINS = set()
    except Exception as e:
        print(f"Ошибка при загрузке списка disposable доменов: {e}")
        DISPOSABLE_DOMAINS = set()

    return DISPOSABLE_DOMAINS

def parse_emails(file_stream, filename=None):
    raw = file_stream.read()
    try:
        text = raw.decode('utf-8', errors='ignore')
    except AttributeError:
        text = raw if isinstance(raw, str) else raw.decode('utf-8', errors='ignore')
    
    emails = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            # Убираем лишние символы и приводим к нижнему регистру
            email = line.lower().strip('.,;:!?()[]{}"\'').strip()
            if email:
                emails.append(email)
    
    return emails

def is_syntax_valid(email: str) -> bool:
    """
    Строгая проверка синтаксиса email согласно RFC 5321/5322
    """
    if not email or not isinstance(email, str):
        return False
    
    # Проверка длины
    if len(email) > MAX_EMAIL_LENGTH:
        return False
    
    # Проверка регулярным выражением
    if not EMAIL_REGEX.match(email):
        return False
    
    # Разбор на части
    try:
        local_part, domain = email.split('@', 1)
    except ValueError:
        return False
    
    # Проверка длины частей
    if len(local_part) > MAX_LOCAL_LENGTH or len(domain) > MAX_DOMAIN_LENGTH:
        return False
    
    # Проверка локальной части
    if not local_part or local_part.startswith('.') or local_part.endswith('.'):
        return False
    
    # Проверка домена
    if not domain or domain.startswith('.') or domain.endswith('.'):
        return False
    
    # Проверка на двойные точки
    if '..' in local_part or '..' in domain:
        return False
    
    # Проверка на недопустимые символы в домене
    if not re.match(r'^[a-zA-Z0-9.-]+$', domain):
        return False
    
    return True

def has_mx_record(domain: str) -> bool:
    """
    Проверка наличия MX-записей с таймаутом
    """
    try:
        # Устанавливаем таймаут для DNS-запросов
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 10
        
        answers = resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout, Exception):
        return False

def has_a_record(domain: str) -> bool:
    """
    Проверка наличия A-записей (IP адресов)
    """
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 10
        
        answers = resolver.resolve(domain, 'A')
        return len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout, Exception):
        return False

def is_reserved_domain(domain: str) -> bool:
    """
    Проверка на зарезервированные домены
    """
    domain_lower = domain.lower()
    
    # Проверка TLD
    tld = domain_lower.split('.')[-1]
    if tld in RESERVED_TLDS:
        return True
    
    # Проверка SLD
    if domain_lower in RESERVED_SLDS:
        return True
    
    # Проверка на IP-адреса
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', domain):
        return True
    
    return False

def is_disposable_domain(domain: str) -> bool:
    """
    Проверка на disposable домены
    """
    disposable_domains = load_disposable_domains()
    return domain.lower() in disposable_domains

def classify_email(email: str) -> str:
    """
    Строгая классификация email адресов:
    1) Синтаксис → INVALID
    2) Зарезервированные домены → INVALID  
    3) Временные/дроп-домены → BLACKLIST
    4) Нет MX записей → INVALID (MX обязательны для email)
    5) Иначе → VALID
    """
    # 1. Синтаксическая проверка
    if not is_syntax_valid(email):
        return Contact.INVALID
    
    # 2. Извлечение домена
    try:
        domain = email.split('@', 1)[1].lower()
    except (ValueError, IndexError):
        return Contact.INVALID
    
    # 3. Проверка на зарезервированные домены
    if is_reserved_domain(domain):
        return Contact.INVALID
    
    # 4. Проверка на disposable домены
    if is_disposable_domain(domain):
        return Contact.BLACKLIST
    
    # 5. Проверка MX записей (обязательны для email)
    if not has_mx_record(domain):
        return Contact.INVALID
    
    return Contact.VALID

def validate_email_strict(email: str) -> dict:
    """
    Расширенная валидация с детальной информацией
    """
    result = {
        'email': email,
        'is_valid': False,
        'status': Contact.INVALID,
        'errors': [],
        'warnings': []
    }
    
    # Синтаксическая проверка
    if not is_syntax_valid(email):
        result['errors'].append('Неверный синтаксис email адреса')
        return result
    
    try:
        domain = email.split('@', 1)[1].lower()
    except (ValueError, IndexError):
        result['errors'].append('Не удалось извлечь домен')
        return result
    
    # Проверка зарезервированных доменов
    if is_reserved_domain(domain):
        result['errors'].append('Зарезервированный домен')
        return result
    
    # Проверка disposable доменов
    if is_disposable_domain(domain):
        result['status'] = Contact.BLACKLIST
        result['warnings'].append('Временный email домен')
        return result
    
    # Проверка MX записей (обязательны для email)
    if not has_mx_record(domain):
        result['errors'].append('Домен не имеет MX записей (не может принимать почту)')
        return result
    
    # Дополнительная проверка A записей (для информации)
    if not has_a_record(domain):
        result['warnings'].append('Домен не имеет A записей (IP адресов)')
    
    result['is_valid'] = True
    result['status'] = Contact.VALID
    return result
