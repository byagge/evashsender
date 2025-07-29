from django.contrib import admin
from .models import SupportTicket, SupportMessage, SupportCategory, SupportAttachment


@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'ticket_subject', 'ticket_user', 'ticket_status', 'ticket_priority', 'ticket_category', 'ticket_assigned_to', 'ticket_created_at']
    list_filter = ['ticket_status', 'ticket_priority', 'ticket_category', 'ticket_created_at']
    search_fields = ['ticket_subject', 'ticket_description', 'ticket_user__email']
    readonly_fields = ['ticket_id', 'ticket_created_at', 'ticket_updated_at']
    ordering = ['-ticket_created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('ticket_id', 'ticket_user', 'ticket_subject', 'ticket_description', 'ticket_category', 'ticket_priority')
        }),
        ('Статус и назначение', {
            'fields': ('ticket_status', 'ticket_assigned_to', 'ticket_resolved_at', 'ticket_closed_at')
        }),
        ('Метаданные', {
            'fields': ('ticket_created_at', 'ticket_updated_at', 'ticket_user_agent', 'ticket_ip_address'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'message_ticket', 'message_author', 'message_staff_reply', 'message_internal', 'message_created_at']
    list_filter = ['message_staff_reply', 'message_internal', 'message_created_at']
    search_fields = ['message_text', 'message_ticket__ticket_subject', 'message_author__email']
    readonly_fields = ['message_id', 'message_created_at', 'message_updated_at']
    ordering = ['-message_created_at']


@admin.register(SupportAttachment)
class SupportAttachmentAdmin(admin.ModelAdmin):
    list_display = ['attachment_id', 'attachment_filename', 'attachment_ticket', 'attachment_message', 'attachment_file_size', 'attachment_uploaded_at']
    list_filter = ['attachment_uploaded_at']
    search_fields = ['attachment_filename', 'attachment_ticket__ticket_subject']
    readonly_fields = ['attachment_id', 'attachment_uploaded_at']
    ordering = ['-attachment_uploaded_at'] 