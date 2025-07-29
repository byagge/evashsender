from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    list_display = ('email', 'full_name', 'is_email_verified', 'is_verified', 'is_trusted_user', 
                   'current_plan', 'plan_expiry', 'emails_sent_today', 'date_joined', 'status')
    list_filter = ('is_email_verified', 'is_verified', 'is_active', 'is_staff', 'is_trusted_user', 
                  'current_plan', 'date_joined')
    search_fields = ('email', 'full_name')
    date_hierarchy = 'date_joined'
    readonly_fields = ('date_joined', 'emails_sent_today')
    actions = ['mark_as_trusted', 'mark_as_verified', 'deactivate_users']

    fieldsets = (
        (None, {'fields': ('email', 'full_name', 'password')}),
        ('Статус', {'fields': ('is_email_verified', 'is_verified', 'is_trusted_user', 'is_active', 'is_staff')}),
        ('Информация о тарифе', {'fields': ('current_plan', 'plan_expiry', 'emails_sent_today')}),
        ('Разрешения', {'fields': ('groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'current_plan', 'is_staff', 'is_active')}
        ),
    )
    ordering = ('email',)

    def status(self, obj):
        if not obj.is_active:
            return format_html('<span style="color: red;">Неактивен</span>')
        if not obj.is_email_verified:
            return format_html('<span style="color: orange;">Email не подтвержден</span>')
        if not obj.is_verified:
            return format_html('<span style="color: orange;">Не верифицирован</span>')
        if obj.is_trusted_user:
            return format_html('<span style="color: green;">Доверенный</span>')
        return format_html('<span style="color: blue;">Активен</span>')
    status.short_description = 'Статус'

    def mark_as_trusted(self, request, queryset):
        queryset.update(is_trusted_user=True)
    mark_as_trusted.short_description = 'Отметить как доверенных'

    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified=True)
    mark_as_verified.short_description = 'Отметить как верифицированных'

    def deactivate_users(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_users.short_description = 'Деактивировать пользователей'
