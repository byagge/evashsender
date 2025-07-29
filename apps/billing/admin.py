from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import PlanType, Plan, PurchasedPlan, BillingSettings


@admin.register(PlanType)
class PlanTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'plan_type', 'subscribers', 'emails_per_month', 
        'max_emails_per_day', 'price', 'discount', 'final_price', 
        'is_active', 'is_featured', 'sort_order'
    ]
    list_filter = ['plan_type', 'is_active', 'is_featured', 'created_at']
    search_fields = ['title']
    list_editable = ['is_active', 'is_featured', 'sort_order', 'price', 'discount']
    ordering = ['sort_order', 'price']
    
    fieldsets = (
        (_('Основная информация'), {
            'fields': ('title', 'plan_type', 'is_active', 'is_featured', 'sort_order')
        }),
        (_('Лимиты'), {
            'fields': ('subscribers', 'emails_per_month', 'max_emails_per_day')
        }),
        (_('Ценообразование'), {
            'fields': ('price', 'discount')
        }),
    )
    
    def final_price(self, obj):
        """Отображение финальной цены с учетом скидки"""
        final = obj.get_final_price()
        if obj.discount > 0:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">{}₽</span> '
                '<span style="color: #d32f2f; font-weight: bold;">{}₽</span>',
                obj.price, final
            )
        return f"{final}₽"
    final_price.short_description = _("Финальная цена")


@admin.register(PurchasedPlan)
class PurchasedPlanAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'start_date', 'end_date', 'is_active', 
        'auto_renew', 'amount_paid', 'days_remaining', 'status'
    ]
    list_filter = ['is_active', 'auto_renew', 'start_date', 'end_date', 'plan__plan_type']
    search_fields = ['user__email', 'user__full_name', 'plan__title', 'transaction_id']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        (_('Пользователь и план'), {
            'fields': ('user', 'plan')
        }),
        (_('Период действия'), {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        (_('Оплата'), {
            'fields': ('auto_renew', 'payment_method', 'transaction_id', 'amount_paid')
        }),
        (_('Системная информация'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def days_remaining(self, obj):
        """Количество дней до истечения"""
        days = obj.days_remaining()
        if days == 0:
            return format_html('<span style="color: #d32f2f;">Истек</span>')
        elif days <= 7:
            return format_html('<span style="color: #f57c00;">{} дн.</span>', days)
        else:
            return f"{days} дн."
    days_remaining.short_description = _("Дней осталось")
    
    def status(self, obj):
        """Статус тарифа"""
        if obj.is_expired():
            return format_html('<span style="color: #d32f2f;">Истек</span>')
        elif obj.is_active:
            return format_html('<span style="color: #388e3c;">Активен</span>')
        else:
            return format_html('<span style="color: #999;">Неактивен</span>')
    status.short_description = _("Статус")


@admin.register(BillingSettings)
class BillingSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'free_plan_subscribers', 'free_plan_emails', 'free_plan_daily_limit',
        'currency', 'tax_rate'
    ]
    
    def has_add_permission(self, request):
        """Запретить создание дополнительных записей настроек"""
        return not BillingSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Запретить удаление настроек"""
        return False
