from django.contrib import admin
from .models import EmailTemplate

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display  = ('title','owner','is_draft','send_count','updated_at')
    list_filter   = ('is_draft','owner')
    search_fields = ('title','plain_text_content')
    readonly_fields= ('send_count','created_at','updated_at')
