# emails/utils.py
import dns.resolver

def has_spf(domain_name):
    try:
        answers = dns.resolver.resolve(domain_name, 'TXT')
        for r in answers:
            txt = r.to_text().strip('"')
            if txt.startswith('v=spf1'):
                return True
    except Exception:
        pass
    return False

def has_dkim(domain_name, selector='default'):
    try:
        # например для selector._domainkey.domain.com
        name = f'{selector}._domainkey.{domain_name}'
        answers = dns.resolver.resolve(name, 'TXT')
        return len(answers) > 0
    except Exception:
        return False
