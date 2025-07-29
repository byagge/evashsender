from django.contrib import admin
from .models import Campaign, EmailTracking, CampaignStats, CampaignRecipient

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'status', 'created_at', 'sent_at')
    list_filter = ('status', 'created_at', 'sent_at')
    search_fields = ('name', 'subject', 'user__email')
    filter_horizontal = ('contact_lists',)
    readonly_fields = ('created_at', 'updated_at', 'sent_at')

@admin.register(EmailTracking)
class EmailTrackingAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'contact', 'sent_at', 'delivered_at', 'opened_at', 'clicked_at')
    list_filter = ('sent_at', 'delivered_at', 'opened_at', 'clicked_at')
    search_fields = ('campaign__name', 'contact__email')

@admin.register(CampaignStats)
class CampaignStatsAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'contact_list', 'emails_sent', 'opens_count', 'clicks_count', 'bounces_count')
    list_filter = ('campaign', 'contact_list')
    search_fields = ('campaign__name', 'contact_list__name')

@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'contact', 'created_at', 'is_sent', 'sent_at')
    list_filter = ('is_sent', 'created_at', 'sent_at')
    search_fields = ('campaign__name', 'contact__email')
