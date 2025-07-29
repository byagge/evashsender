import re
import dns.resolver
import requests
from .models import Contact

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Кэш для загруженных disposable-доменов
DISPOSABLE_DOMAINS = None

def load_disposable_domains():
    """
    Загружает список disposable-доменов только один раз при первом вызове.
    """
    global DISPOSABLE_DOMAINS
    if DISPOSABLE_DOMAINS is not None:
        return DISPOSABLE_DOMAINS

    url = "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            DISPOSABLE_DOMAINS = set(
                line.strip().lower()
                for line in response.text.splitlines()
                if line.strip()
            )
            print(f"{len(DISPOSABLE_DOMAINS)} доменов загружено.")
        else:
            print("Не удалось загрузить список disposable-доменов.")
            DISPOSABLE_DOMAINS = set()
    except Exception as e:
        print(f"Ошибка при загрузке списка: {e}")
        DISPOSABLE_DOMAINS = set()

    return DISPOSABLE_DOMAINS

def parse_emails(file_stream, filename=None):
    raw = file_stream.read()
    try:
        text = raw.decode('utf-8', errors='ignore')
    except AttributeError:
        text = raw if isinstance(raw, str) else raw.decode('utf-8', errors='ignore')
    return [line.strip() for line in text.splitlines() if line.strip()]

def is_syntax_valid(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))

def has_mx_record(domain: str) -> bool:
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except Exception:
        return False

def classify_email(email: str) -> str:
    """
    Классифицирует **любой** email:
      1) Синтаксис → INVALID
      2) Временный/дроп-домен → BLACKLIST
      3) Нет MX → INVALID
      4) Иначе → VALID
    """
    if not is_syntax_valid(email):
        return Contact.INVALID

    domain = email.split('@', 1)[1].lower()
    if domain in load_disposable_domains():
        return Contact.BLACKLIST

    if not has_mx_record(domain):
        return Contact.INVALID

    return Contact.VALID
