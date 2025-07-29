# core/apps/emails/admin.py

from django.contrib import admin
from .models import Domain, SenderEmail

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = (
        'domain_name', 'owner',
        'is_verified', 'spf_verified', 'dkim_verified', 'created_at'
    )
    list_filter = (
        'is_verified', 'spf_verified', 'dkim_verified', 'created_at'
    )
    search_fields = ('domain_name', 'owner__email')
    readonly_fields = (
        'verification_token', 'created_at',
        'public_key', 'private_key_path', 'dkim_dns_record'
    )
    fieldsets = (
        ('Основная информация', {
            'fields': ('domain_name', 'owner')
        }),
        ('Статус верификации', {
            'fields': ('is_verified', 'spf_verified', 'dkim_verified')
        }),
        ('DKIM‑ключи', {
            'fields': ('public_key', 'private_key_path', 'dkim_dns_record'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('verification_token', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SenderEmail)
class SenderEmailAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'domain', 'owner',
        'is_verified', 'created_at', 'verified_at'
    )
    list_filter = ('is_verified', 'created_at', 'verified_at')
    search_fields = (
        'email', 'domain__domain_name', 'owner__email'
    )
    readonly_fields = (
        'verification_token', 'created_at', 'verified_at'
    )
    fieldsets = (
        ('Основная информация', {
            'fields': ('email', 'domain', 'owner')
        }),
        ('Статус верификации', {
            'fields': ('is_verified', 'verified_at')
        }),
        ('Системная информация', {
            'fields': ('verification_token', 'created_at'),
            'classes': ('collapse',)
        }),
    )
