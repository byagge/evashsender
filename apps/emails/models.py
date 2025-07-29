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
    domain_name = models.CharField(max_length=255, unique=True)
    is_verified = models.BooleanField(default=False)
    spf_verified = models.BooleanField(default=False)
    dkim_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # DKIM fields
    dkim_selector = models.CharField(max_length=100, default=DKIM_SELECTOR)
    public_key = models.TextField(blank=True)
    private_key_path = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return self.domain_name

    @property
    def dkim_dns_record(self):
        # returns the DNS TXT record for DKIM
        name = f"{self.dkim_selector}._domainkey.{self.domain_name}"
        value = self.public_key.strip().split(' ', 1)[1] if 'p=' in self.public_key else self.public_key
        return f"{name} IN TXT \"{value}\""


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


@receiver(post_save, sender=Domain)
def generate_dkim_keys(sender, instance, created, **kwargs):
    """
    Signal: Generate DKIM keys and update OpenDKIM config when a new Domain is created.
    """
    if created or not instance.dkim_verified:
        domain = instance.domain_name
        selector = instance.dkim_selector
        domain_dir = os.path.join(DKIM_KEYS_DIR, domain)
        os.makedirs(domain_dir, exist_ok=True)

        # Generate keys
        subprocess.run([
            'opendkim-genkey',
            '-D', domain_dir,
            '-d', domain,
            '-s', selector
        ], check=True)

        private_path = os.path.join(domain_dir, f'{selector}.private')
        public_txt = os.path.join(domain_dir, f'{selector}.txt')

        # Read public key
        with open(public_txt, 'r') as f:
            public_key = f.read()

        # Update instance fields
        instance.public_key = public_key
        instance.private_key_path = private_path
        instance.save(update_fields=['public_key', 'private_key_path'])

        # Append to OpenDKIM config
        keytable = f"{selector}._domainkey.{domain} {domain}:{selector}:{private_path}\n"
        signingtable = f"*@{domain} {selector}._domainkey.{domain}\n"
        trustedhosts = f"{domain}\n"

        with open('/etc/opendkim/KeyTable', 'a') as kt, \
             open('/etc/opendkim/SigningTable', 'a') as st, \
             open('/etc/opendkim/TrustedHosts', 'a') as th:
            kt.write(keytable)
            st.write(signingtable)
            th.write(trustedhosts)

        # Restart OpenDKIM service to apply changes
        subprocess.run(['systemctl', 'restart', 'opendkim'], check=True)
        # Mark as verified so it doesn't regenerate constantly
        instance.dkim_verified = True
        instance.save(update_fields=['dkim_verified'])

