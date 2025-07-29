from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Plan, PurchasedPlan, User

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'subscribers', 'discount', 'max_emails_per_day', 'price', 'active_users_count')
    search_fields = ('title',)
    list_filter = ('price', 'max_emails_per_day')
    readonly_fields = ('subscribers',)
    
    def active_users_count(self, obj):
        return obj.users.filter(is_active=True).count()
    active_users_count.short_description = 'Активных пользователей'

@admin.register(PurchasedPlan)
class PurchasedPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active', 'days_remaining')
    list_filter = ('is_active', 'plan', 'start_date', 'end_date')
    search_fields = ('user__email', 'user__full_name')
    date_hierarchy = 'start_date'
    readonly_fields = ('is_active',)
    
    def days_remaining(self, obj):
        if obj.end_date:
            remaining = obj.end_date - timezone.now()
            days = remaining.days
            if days > 0:
                return format_html('<span style="color: green;">{} дней</span>', days)
            elif days == 0:
                return format_html('<span style="color: orange;">Истекает сегодня</span>')
            else:
                return format_html('<span style="color: red;">Истек {} дней назад</span>', abs(days))
        return '-'
    days_remaining.short_description = 'Осталось дней'

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'full_name', 'is_email_verified', 'is_verified', 'is_trusted_user', 
                   'current_plan', 'plan_expiry', 'emails_sent_today', 'date_joined', 'status')
    list_filter = ('is_email_verified', 'is_verified', 'is_active', 'is_staff', 'is_trusted_user', 
                  'current_plan', 'date_joined')
    search_fields = ('email', 'full_name')
    date_hierarchy = 'date_joined'
    readonly_fields = ('date_joined', 'emails_sent_today')
    actions = ['mark_as_trusted', 'mark_as_verified', 'deactivate_users']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'full_name', 'password')
        }),
        ('Статус', {
            'fields': ('is_email_verified', 'is_verified', 'is_trusted_user', 'is_active', 'is_staff')
        }),
        ('Информация о тарифе', {
            'fields': ('current_plan', 'plan_expiry', 'emails_sent_today')
        }),
        ('Разрешения', {
            'fields': ('groups', 'user_permissions')
        }),
    )
    
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
