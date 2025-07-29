from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        
        # Получаем бесплатный план из billing app
        from apps.billing.models import Plan, PlanType, BillingSettings
        free_plan = Plan.objects.filter(title__icontains='бесплат').first()
        if not free_plan:
            # Если бесплатного плана нет, создаем его
            settings = BillingSettings.get_settings()
            # Получаем тип плана Free (ID=1)
            free_plan_type = PlanType.objects.get(id=1)
            free_plan = Plan.objects.create(
                title="Бесплатный",
                plan_type=free_plan_type,
                subscribers=settings.free_plan_subscribers,
                emails_per_month=settings.free_plan_emails,
                max_emails_per_day=settings.free_plan_daily_limit,
                price=0
            )
        
        user = self.model(email=email, current_plan=free_plan, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)  # например, ручная модерация
    is_trusted_user = models.BooleanField(default=False)  # доверенный пользователь
    current_plan = models.ForeignKey('billing.Plan', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    plan_expiry = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    emails_sent_today = models.PositiveIntegerField(default=0)
    is_staff = models.BooleanField(default=False)  # нужно для админки
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return self.email

    def has_exceeded_daily_limit(self):
        if not self.current_plan:
            # Если нет плана, используем бесплатные лимиты
            from apps.billing.models import BillingSettings
            settings = BillingSettings.get_settings()
            return self.emails_sent_today >= settings.free_plan_daily_limit
        return self.emails_sent_today >= self.current_plan.max_emails_per_day
