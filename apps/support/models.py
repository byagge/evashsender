from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class SupportCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['sort_order', 'name']


class SupportTicket(models.Model):
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_WAITING = 'waiting'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'
    
    STATUS_CHOICES = (
        (STATUS_OPEN, 'Открыт'),
        (STATUS_IN_PROGRESS, 'В работе'),
        (STATUS_WAITING, 'Ожидает ответа'),
        (STATUS_RESOLVED, 'Решён'),
        (STATUS_CLOSED, 'Закрыт'),
    )
    
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    
    PRIORITY_CHOICES = (
        (PRIORITY_LOW, 'Низкий'),
        (PRIORITY_MEDIUM, 'Средний'),
        (PRIORITY_HIGH, 'Высокий'),
        (PRIORITY_URGENT, 'Срочный'),
    )
    
    ticket_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    ticket_category = models.ForeignKey(SupportCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    ticket_subject = models.CharField(max_length=255)
    ticket_description = models.TextField()
    ticket_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    ticket_priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    
    ticket_assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_support_tickets'
    )
    
    ticket_created_at = models.DateTimeField(auto_now_add=True)
    ticket_updated_at = models.DateTimeField(auto_now=True)
    ticket_resolved_at = models.DateTimeField(null=True, blank=True)
    ticket_closed_at = models.DateTimeField(null=True, blank=True)
    
    ticket_user_agent = models.TextField(blank=True)
    ticket_ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self):
        return f"#{self.ticket_id.hex[:8]} - {self.ticket_subject}"
    
    class Meta:
        ordering = ['-ticket_created_at']


class SupportMessage(models.Model):
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message_ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='ticket_messages')
    message_author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_messages')
    
    message_text = models.TextField()
    message_internal = models.BooleanField(default=False)
    message_staff_reply = models.BooleanField(default=False)
    
    message_created_at = models.DateTimeField(auto_now_add=True)
    message_updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Сообщение в тикете {self.message_ticket.ticket_id.hex[:8]} от {self.message_author.email}"
    
    def save(self, *args, **kwargs):
        if not self.message_staff_reply:
            self.message_staff_reply = self.message_author.is_staff
        
        super().save(*args, **kwargs)
        
        if self.message_staff_reply:
            if self.message_ticket.ticket_status == SupportTicket.STATUS_WAITING:
                self.message_ticket.ticket_status = SupportTicket.STATUS_IN_PROGRESS
                self.message_ticket.save(update_fields=['ticket_status'])
        else:
            if self.message_ticket.ticket_status in [SupportTicket.STATUS_OPEN, SupportTicket.STATUS_IN_PROGRESS]:
                self.message_ticket.ticket_status = SupportTicket.STATUS_WAITING
                self.message_ticket.save(update_fields=['ticket_status'])
    
    class Meta:
        ordering = ['message_created_at']


class SupportAttachment(models.Model):
    attachment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attachment_ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='ticket_attachments')
    attachment_message = models.ForeignKey(SupportMessage, on_delete=models.CASCADE, related_name='message_attachments')
    
    attachment_file = models.FileField(upload_to='support_attachments/')
    attachment_filename = models.CharField(max_length=255)
    attachment_file_size = models.PositiveIntegerField()
    attachment_mime_type = models.CharField(max_length=100)
    
    attachment_uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.attachment_filename} ({self.attachment_ticket.ticket_id.hex[:8]})"
    
    class Meta:
        pass 