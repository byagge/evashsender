from django.core.management.base import BaseCommand
from apps.accounts.models import User

class Command(BaseCommand):
    help = 'Делает пользователя доверенным (is_trusted_user=True)'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email пользователя')

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            user = User.objects.get(email=email)
            user.is_trusted_user = True
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Пользователь {email} теперь доверенный (is_trusted_user=True)')
            )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Пользователь с email {email} не найден')
            ) 