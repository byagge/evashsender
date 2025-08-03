from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class PlanType(models.Model):
    """Типы тарифов (Free, Subscribers, Letters)"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Тип тарифа")
        verbose_name_plural = _("Типы тарифов")


class Plan(models.Model):
    """Тарифные планы"""
    title = models.CharField(max_length=100)
    plan_type = models.ForeignKey(PlanType, on_delete=models.CASCADE, related_name='plans')
    subscribers = models.PositiveIntegerField(default=0, help_text=_("Количество подписчиков"))
    emails_per_month = models.PositiveIntegerField(default=0, help_text=_("Количество писем в месяц"))
    max_emails_per_day = models.PositiveIntegerField(default=0, help_text=_("Максимум писем в день"))
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text=_("Цена в рублях"))
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text=_("Процент скидки"))
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text=_("Рекомендуемый тариф"))
    sort_order = models.PositiveIntegerField(default=0, help_text=_("Порядок сортировки"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.price}₽"
    
    def get_final_price(self):
        """Получить финальную цену с учетом скидки"""
        if self.discount > 0:
            return self.price * (1 - self.discount / 100)
        return self.price
    
    class Meta:
        verbose_name = _("Тарифный план")
        verbose_name_plural = _("Тарифные планы")
        ordering = ['sort_order', 'price']


class PurchasedPlan(models.Model):
    """Купленные тарифы пользователей"""
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='purchased_plans')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    auto_renew = models.BooleanField(default=False, help_text=_("Автопродление"))
    payment_method = models.CharField(max_length=50, blank=True, help_text=_("Способ оплаты"))
    transaction_id = models.CharField(max_length=100, blank=True, help_text=_("ID транзакции"))
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    emails_sent = models.PositiveIntegerField(default=0, help_text=_("Количество отправленных писем"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.title} ({self.start_date.date()} - {self.end_date.date()})"
    
    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError(_("Дата окончания должна быть позже даты начала"))
    
    def save(self, *args, **kwargs):
        self.clean()
        is_new = not self.pk
        
        super().save(*args, **kwargs)
        
        if is_new and self.is_active:
            # Обновляем текущий план пользователя
            self.user.current_plan = self.plan
            self.user.plan_expiry = self.end_date
            self.user.save(update_fields=['current_plan', 'plan_expiry'])
    
    def is_expired(self):
        """Проверить, истек ли тариф"""
        return timezone.now() > self.end_date
    
    def days_remaining(self):
        """Количество дней до истечения"""
        if self.is_expired():
            return 0
        return (self.end_date - timezone.now()).days
    
    def get_emails_remaining(self):
        """Получить количество оставшихся писем"""
        if self.plan.plan_type.name == 'Letters':
            return max(0, self.plan.emails_per_month - self.emails_sent)
        return None  # Для тарифов с подписчиками лимит по времени
    
    def can_send_emails(self, count=1):
        """Проверить, можно ли отправить указанное количество писем"""
        if self.plan.plan_type.name == 'Letters':
            return self.get_emails_remaining() >= count
        # Для тарифов с подписчиками проверяем только срок действия
        return not self.is_expired()
    
    def add_emails_sent(self, count=1):
        """Добавить количество отправленных писем"""
        if self.plan.plan_type.name == 'Letters':
            self.emails_sent += count
            self.save(update_fields=['emails_sent'])
    
    class Meta:
        verbose_name = _("Купленный тариф")
        verbose_name_plural = _("Купленные тарифы")
        ordering = ['-start_date']


class CloudPaymentsTransaction(models.Model):
    """Транзакции CloudPayments"""
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Ожидает оплаты'),
        (STATUS_COMPLETED, 'Оплачено'),
        (STATUS_FAILED, 'Ошибка'),
        (STATUS_CANCELLED, 'Отменено'),
    )
    
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='cloudpayments_transactions')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, null=True, blank=True)
    cloudpayments_id = models.CharField(max_length=100, unique=True, help_text=_("ID транзакции в CloudPayments"))
    amount = models.DecimalField(max_digits=8, decimal_places=2, help_text=_("Сумма в рублях"))
    currency = models.CharField(max_length=3, default='RUB', help_text=_("Валюта"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_method = models.CharField(max_length=50, blank=True, help_text=_("Способ оплаты"))
    description = models.TextField(blank=True, help_text=_("Описание платежа"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Дополнительные поля от CloudPayments
    card_last_four = models.CharField(max_length=4, blank=True, help_text=_("Последние 4 цифры карты"))
    card_type = models.CharField(max_length=20, blank=True, help_text=_("Тип карты"))
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.amount}₽ ({self.status})"
    
    def mark_as_completed(self):
        """Отметить транзакцию как завершенную"""
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def mark_as_failed(self):
        """Отметить транзакцию как неудачную"""
        self.status = self.STATUS_FAILED
        self.save(update_fields=['status'])
    
    class Meta:
        verbose_name = _("Транзакция CloudPayments")
        verbose_name_plural = _("Транзакции CloudPayments")
        ordering = ['-created_at']


class BillingSettings(models.Model):
    """Настройки биллинга"""
    free_plan_subscribers = models.PositiveIntegerField(default=100, help_text=_("Количество подписчиков в бесплатном тарифе"))
    free_plan_emails = models.PositiveIntegerField(default=100, help_text=_("Количество писем в бесплатном тарифе"))
    free_plan_daily_limit = models.PositiveIntegerField(default=50, help_text=_("Дневной лимит писем в бесплатном тарифе"))
    
    # CloudPayments настройки
    cloudpayments_public_id = models.CharField(max_length=100, blank=True, help_text=_("Public ID CloudPayments"))
    cloudpayments_api_secret = models.CharField(max_length=100, blank=True, help_text=_("API Secret CloudPayments"))
    cloudpayments_test_mode = models.BooleanField(default=True, help_text=_("Тестовый режим CloudPayments"))
    
    # Настройки автопродления
    auto_renewal_enabled = models.BooleanField(default=True, help_text=_("Включить автопродление"))
    auto_renewal_days_before = models.PositiveIntegerField(default=3, help_text=_("Дней до истечения для автопродления"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return "Настройки биллинга"
    
    @classmethod
    def get_settings(cls):
        """Получить настройки (создать если не существуют)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    class Meta:
        verbose_name = _("Настройка биллинга")
        verbose_name_plural = _("Настройки биллинга")
