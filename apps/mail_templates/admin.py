from django.contrib import admin
from .models import EmailTemplate, TemplateImage


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'is_draft', 'send_count', 'created_at', 'updated_at']
    list_filter = ['is_draft', 'created_at', 'updated_at']
    search_fields = ['title', 'owner__username', 'owner__email']
    readonly_fields = ['send_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('owner', 'title', 'is_draft')
        }),
        ('Контент', {
            'fields': ('html_content', 'ck_content', 'plain_text_content'),
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': ('send_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TemplateImage)
class TemplateImageAdmin(admin.ModelAdmin):
    list_display = ['filename', 'owner', 'file_size_mb', 'dimensions', 'created_at']
    list_filter = ['created_at']
    search_fields = ['filename', 'owner__username', 'owner__email']
    readonly_fields = ['file_size', 'width', 'height', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('owner', 'image', 'filename', 'alt_text')
        }),
        ('Технические данные', {
            'fields': ('file_size', 'width', 'height', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def file_size_mb(self, obj):
        return obj.get_file_size_mb()
    file_size_mb.short_description = 'Размер (МБ)'

    def dimensions(self, obj):
        return obj.get_dimensions()
    dimensions.short_description = 'Размеры'
