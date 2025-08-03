# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_create_plan_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchasedplan',
            name='emails_sent',
            field=models.PositiveIntegerField(default=0, help_text='Количество отправленных писем'),
        ),
    ] 