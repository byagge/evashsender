from django.db import migrations

def create_plan_types(apps, schema_editor):
    PlanType = apps.get_model('billing', 'PlanType')
    
    # Создаем типы планов
    PlanType.objects.get_or_create(
        id=1,
        defaults={
            'name': 'Free',
            'description': 'Бесплатный тариф для новых пользователей',
            'is_active': True
        }
    )
    
    PlanType.objects.get_or_create(
        id=2,
        defaults={
            'name': 'Subscribers',
            'description': 'Тарифы по количеству подписчиков',
            'is_active': True
        }
    )
    
    PlanType.objects.get_or_create(
        id=3,
        defaults={
            'name': 'Letters',
            'description': 'Тарифы по количеству писем',
            'is_active': True
        }
    )

def reverse_create_plan_types(apps, schema_editor):
    PlanType = apps.get_model('billing', 'PlanType')
    PlanType.objects.filter(id__in=[1, 2, 3]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_plan_types, reverse_create_plan_types),
    ] 