# core/apps/emails/models.py

import os
import uuid
import subprocess
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

DKIM_KEYS_DIR = '/etc/opendkim/keys'
DKIM_SELECTOR = 'default'

class Domain(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='domains'
    )
    domain_name = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    spf_verified = models.BooleanField(default=False)
    dkim_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # DKIM fields
    dkim_selector = models.CharField(max_length=100, default=DKIM_SELECTOR)
    public_key = models.TextField(blank=True)
    private_key_path = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = ['owner', 'domain_name']

    def __str__(self):
        return self.domain_name

    def generate_dkim_keys(self):
        """Генерирует DKIM ключи для домена"""
        try:
            from .dkim_service import DKIMService
            service = DKIMService()
            
            print(f"Generating DKIM keys for domain: {self.domain_name}")
            result = service.generate_keys(self.domain_name)
            if result:
                public_key, private_key = result
                print(f"DKIM keys generated for {self.domain_name}, public_key length: {len(public_key)}")
                
                self.public_key = public_key
                self.private_key_path = private_key
                self.save(update_fields=['public_key', 'private_key_path'])
                
                # Обновляем объект из базы данных
                self.refresh_from_db()
                print(f"Domain {self.domain_name} saved with public_key: {bool(self.public_key)}")
                return True
            else:
                print(f"Failed to generate DKIM keys for {self.domain_name}")
                return False
        except Exception as e:
            print(f"Error generating DKIM keys for {self.domain_name}: {e}")
            return False

    @property
    def dkim_dns_record(self):
        """Возвращает DNS TXT запись для DKIM"""
        print(f"Getting DKIM DNS record for {self.domain_name}, public_key length: {len(self.public_key) if self.public_key else 0}")
        
        if not self.public_key:
            print(f"No public key for domain {self.domain_name}")
            return ""
        
        from .dkim_service import DKIMService
        service = DKIMService()
        dns_record = service.get_dns_record(self.domain_name, self.public_key)
        print(f"Generated DNS record for {self.domain_name}: {dns_record[:100]}...")
        return dns_record


class SenderEmail(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sender_emails'
    )
    email = models.EmailField(unique=True)
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='senders'
    )
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    sender_name = models.CharField(max_length=100, blank=True, default='')
    reply_to = models.EmailField(blank=True, default='')

    def __str__(self):
        return self.email


# Сигнал удален - теперь DKIM генерируется через сервис

