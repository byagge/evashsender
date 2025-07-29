from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from apps.billing.models import Plan, PurchasedPlan
from .models import User

@receiver(post_save, sender=User)
def assign_free_plan(sender, instance, created, **kwargs):
    if created and not PurchasedPlan.objects.filter(user=instance, is_active=True).exists():
        # Находим бесплатный тариф
        free_plan = Plan.objects.filter(price=0, is_active=True).order_by('id').first()
        if free_plan:
            PurchasedPlan.objects.create(
                user=instance,
                plan=free_plan,
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=30),
                is_active=True,
                auto_renew=False,
                payment_method='free',
                transaction_id='FREE-INIT',
                amount_paid=0
            )
