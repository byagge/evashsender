# core/apps/emails/models.py

import uuid
from django.db import models
from django.conf import settings

class Domain(models.Model):
    owner               = models.ForeignKey(settings.AUTH_USER_MODEL,
                                            on_delete=models.CASCADE,
                                            related_name='domains')
    domain_name         = models.CharField(max_length=255, unique=True)
    is_verified         = models.BooleanField(default=False)
    spf_verified        = models.BooleanField(default=False)
    dkim_verified       = models.BooleanField(default=False)
    verification_token  = models.UUIDField(default=uuid.uuid4,
                                          editable=False,
                                          unique=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.domain_name


class SenderEmail(models.Model):
    owner               = models.ForeignKey(settings.AUTH_USER_MODEL,
                                            on_delete=models.CASCADE,
                                            related_name='sender_emails')
    email               = models.EmailField(unique=True)
    domain              = models.ForeignKey(Domain,
                                            on_delete=models.CASCADE,
                                            related_name='senders')
    is_verified         = models.BooleanField(default=False)
    verification_token  = models.UUIDField(default=uuid.uuid4,
                                          editable=False,
                                          unique=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    verified_at         = models.DateTimeField(null=True, blank=True)
    sender_name         = models.CharField(max_length=100, blank=True, default='')
    reply_to            = models.EmailField(blank=True, default='')

    def __str__(self):
        return self.email
