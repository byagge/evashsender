import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q

class ContactList(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contact_lists')
    name = models.CharField(max_length=255)
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
    VALID = 'valid'
    INVALID = 'invalid'
    BLACKLIST = 'blacklist'
    STATUS_CHOICES = (
        (VALID, 'Действительный'),
        (INVALID, 'Недействительный'),
        (BLACKLIST, 'В черном списке'),
    )

    contact_list = models.ForeignKey(ContactList, on_delete=models.CASCADE, related_name='contacts')
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=VALID)
    added_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('contact_list', 'email')
        ordering = ['email']

    def __str__(self):
        return self.email

class ImportTask(models.Model):
    """
    Модель для отслеживания фоновых задач импорта
    """
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STATUS_CHOICES = (
        (PENDING, 'Ожидает'),
        (PROCESSING, 'Обрабатывается'),
        (COMPLETED, 'Завершено'),
        (FAILED, 'Ошибка'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_list = models.ForeignKey(ContactList, on_delete=models.CASCADE, related_name='import_tasks')
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    total_emails = models.IntegerField(default=0)
    processed_emails = models.IntegerField(default=0)
    imported_count = models.IntegerField(default=0)
    invalid_count = models.IntegerField(default=0)
    blacklisted_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Import {self.id} - {self.filename}"

    @property
    def progress_percentage(self):
        if self.total_emails == 0:
            return 0
        return min(100, int((self.processed_emails / self.total_emails) * 100))

    @property
    def duration(self):
        if not self.started_at:
            return None
        end_time = self.completed_at or timezone.now()
        return (end_time - self.started_at).total_seconds()
