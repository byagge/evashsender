# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_add_emails_sent_to_purchasedplan'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CloudPaymentsTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cloudpayments_id', models.CharField(help_text='ID транзакции в CloudPayments', max_length=100, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Сумма в рублях', max_digits=8)),
                ('currency', models.CharField(default='RUB', help_text='Валюта', max_length=3)),
                ('status', models.CharField(choices=[('pending', 'Ожидает оплаты'), ('completed', 'Оплачено'), ('failed', 'Ошибка'), ('cancelled', 'Отменено')], default='pending', max_length=20)),
                ('payment_method', models.CharField(blank=True, help_text='Способ оплаты', max_length=50)),
                ('description', models.TextField(blank=True, help_text='Описание платежа')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('card_last_four', models.CharField(blank=True, help_text='Последние 4 цифры карты', max_length=4)),
                ('card_type', models.CharField(blank=True, help_text='Тип карты', max_length=20)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='billing.plan')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cloudpayments_transactions', to='accounts.user')),
            ],
            options={
                'verbose_name': 'Транзакция CloudPayments',
                'verbose_name_plural': 'Транзакции CloudPayments',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterField(
            model_name='billingsettings',
            name='free_plan_emails',
            field=models.PositiveIntegerField(default=100, help_text='Количество писем в бесплатном тарифе'),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='cloudpayments_public_id',
            field=models.CharField(blank=True, help_text='Public ID CloudPayments', max_length=100),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='cloudpayments_api_secret',
            field=models.CharField(blank=True, help_text='API Secret CloudPayments', max_length=100),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='cloudpayments_test_mode',
            field=models.BooleanField(default=True, help_text='Тестовый режим CloudPayments'),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='auto_renewal_enabled',
            field=models.BooleanField(default=True, help_text='Включить автопродление'),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='auto_renewal_days_before',
            field=models.PositiveIntegerField(default=3, help_text='Дней до истечения для автопродления'),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='billingsettings',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ] 