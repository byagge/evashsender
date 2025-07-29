from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models import Count, Q

class ContactList(models.Model):
    owner      = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   related_name='contact_lists')
    name       = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner','name')
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    @property
    def total_contacts(self):
        return self.contacts.count()

    @property
    def valid_count(self):
        return self.contacts.filter(status=Contact.VALID).count()

    @property
    def invalid_count(self):
        return self.contacts.filter(status=Contact.INVALID).count()

    @property
    def blacklisted_count(self):
        return self.contacts.filter(status=Contact.BLACKLIST).count()

    def counts(self):
        agg = self.contacts.aggregate(
            total=Count('id'),
            valid=Count('id', filter=Q(status=Contact.VALID)),
            invalid=Count('id', filter=Q(status=Contact.INVALID)),
            blacklisted=Count('id', filter=Q(status=Contact.BLACKLIST)),
        )
        return agg

class Contact(models.Model):
    VALID     = 'valid'
    INVALID   = 'invalid'
    BLACKLIST = 'blacklist'
    STATUS_CHOICES = [
        (VALID,     'Действительный'),
        (INVALID,   'Недействительный'),
        (BLACKLIST, 'В чёрном списке'),
    ]

    contact_list = models.ForeignKey(ContactList,
                                     on_delete=models.CASCADE,
                                     related_name='contacts')
    email        = models.EmailField()
    status       = models.CharField(max_length=20,
                                    choices=STATUS_CHOICES,
                                    default=VALID)
    added_date   = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('contact_list','email')
        ordering = ['email']

    def __str__(self):
        return self.email
