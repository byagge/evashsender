from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Plan

@receiver(post_migrate)
def create_default_plan(sender, **kwargs):
    if sender.name == 'accounts':
        Plan.objects.get_or_create(title='Free', defaults={
            'price': 0,
            'emails_limit': 100,
            'description': 'Бесплатный план'
        })
