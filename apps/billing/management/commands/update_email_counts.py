from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.billing.models import PurchasedPlan
from apps.billing.utils import update_plan_emails_sent
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Обновляет счётчики отправленных писем в тарифах на основе фактических отправок'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Email пользователя для обновления (если не указан, обновляются все)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет обновлено без внесения изменений',
        )

    def handle(self, *args, **options):
        user_email = options.get('user')
        dry_run = options.get('dry_run')

        if user_email:
            try:
                user = User.objects.get(email=user_email)
                users = [user]
                self.stdout.write(f"Обновляем данные для пользователя: {user_email}")
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Пользователь {user_email} не найден"))
                return
        else:
            users = User.objects.all()
            self.stdout.write(f"Обновляем данные для всех пользователей ({users.count()} пользователей)")

        updated_count = 0
        total_plans = 0

        for user in users:
            active_plans = PurchasedPlan.objects.filter(
                user=user,
                is_active=True,
                end_date__gt=timezone.now()
            )

            for plan in active_plans:
                total_plans += 1
                
                if plan.plan.plan_type.name == 'Letters':
                    # Подсчитываем фактически отправленные письма
                    from apps.campaigns.models import EmailTracking
                    actual_sent = EmailTracking.objects.filter(
                        campaign__user=user,
                        sent_at__gte=plan.start_date,
                        sent_at__lte=plan.end_date
                    ).count()

                    if dry_run:
                        self.stdout.write(
                            f"Пользователь: {user.email}, Тариф: {plan.plan.title}, "
                            f"Текущий счётчик: {plan.emails_sent}, Фактически отправлено: {actual_sent}"
                        )
                    else:
                        if plan.emails_sent != actual_sent:
                            old_count = plan.emails_sent
                            plan.emails_sent = actual_sent
                            plan.save(update_fields=['emails_sent'])
                            updated_count += 1
                            
                            self.stdout.write(
                                f"Обновлён счётчик для {user.email} ({plan.plan.title}): "
                                f"{old_count} → {actual_sent}"
                            )
                        else:
                            self.stdout.write(
                                f"Счётчик для {user.email} ({plan.plan.title}) уже актуален: {actual_sent}"
                            )

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Проверено {total_plans} тарифов"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Обновлено {updated_count} из {total_plans} тарифов"
                )
            ) 