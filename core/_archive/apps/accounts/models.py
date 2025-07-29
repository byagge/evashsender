from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    title = models.CharField(max_length=50)
    subscribers = models.PositiveIntegerField(default=0)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # процент скидки, например 10.00
    max_emails_per_day = models.PositiveIntegerField(default=0)  # ограничение по отправке
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return self.title
    
class PurchasedPlan(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='purchases')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            # при первой покупке — обновим пользователя
            self.user.current_plan = self.plan
            self.user.plan_expiry = self.end_date
            self.user.save()
        super().save(*args, **kwargs)



class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        plan = Plan.objects.filter(title='Free').first()
        user = self.model(email=email, current_plan=plan, **extra_fields)
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
    current_plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
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
            return True  # если нет тарифа — 0 писем
        return self.emails_sent_today >= self.current_plan.max_emails_per_day
