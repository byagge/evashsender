from django.core.management.base import BaseCommand
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from apps.accounts.models import User
from apps.emails.models import SenderEmail, Domain
from apps.mail_templates.models import EmailTemplate
from apps.mailer.models import Contact, ContactList
from apps.campaigns.models import Campaign
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test email sending functionality'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email to send test to')
        parser.add_argument('--user-id', type=int, help='User ID to use for testing')

    def handle(self, *args, **options):
        test_email = options.get('email')
        user_id = options.get('user_id')

        if not test_email:
            self.stdout.write(self.style.ERROR('Please provide --email parameter'))
            return

        try:
            # Get or create test user
            if user_id:
                user = User.objects.get(id=user_id)
            else:
                user = User.objects.first()
                if not user:
                    self.stdout.write(self.style.ERROR('No users found in database'))
                    return

            self.stdout.write(f'Using user: {user.email}')

            # Get or create test domain
            domain, created = Domain.objects.get_or_create(
                owner=user,
                domain_name='vashsender.ru',
                defaults={
                    'is_verified': True,  # Для тестирования считаем домен верифицированным
                    'spf_verified': True,
                    'dkim_verified': True
                }
            )
            if created:
                self.stdout.write(f'Created test domain: {domain.domain_name}')

            # Get or create test sender email
            sender_email, created = SenderEmail.objects.get_or_create(
                owner=user,
                email='test@vashsender.ru',
                defaults={
                    'domain': domain,
                    'sender_name': 'Test Sender',
                    'reply_to': 'reply@vashsender.ru',
                    'is_verified': True  # Для тестирования считаем email верифицированным
                }
            )
            if created:
                self.stdout.write(f'Created test sender email: {sender_email.email}')

            # Get or create test template
            template, created = EmailTemplate.objects.get_or_create(
                owner=user,
                title='Test Template',
                defaults={
                    'html_content': '''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Test Email</title>
                    </head>
                    <body>
                        <h1>Test Email</h1>
                        <p>This is a test email from VashSender.</p>
                        <p>Time: {{content}}</p>
                        <a href="https://vashsender.ru">Visit VashSender</a>
                    </body>
                    </html>
                    '''
                }
            )
            if created:
                self.stdout.write(f'Created test template: {template.title}')

            # Get or create test contact list
            contact_list, created = ContactList.objects.get_or_create(
                owner=user,
                name='Test List',
                defaults={}
            )
            if created:
                self.stdout.write(f'Created test contact list: {contact_list.name}')

            # Get or create test contact
            contact, created = Contact.objects.get_or_create(
                contact_list=contact_list,
                email=test_email,
                defaults={}
            )
            if created:
                self.stdout.write(f'Created test contact: {contact.email}')

            # Add contact to list (if not already added)
            contact_list.contacts.add(contact)

            # Create test campaign
            campaign = Campaign.objects.create(
                user=user,
                name='Test Campaign',
                subject='Test Email Campaign',
                content=f'This email was sent at {timezone.now()}',
                template=template,
                sender_email=sender_email,
                status=Campaign.STATUS_DRAFT
            )
            campaign.contact_lists.add(contact_list)

            self.stdout.write(f'Created test campaign: {campaign.name}')

            # Test direct email sending
            self.stdout.write('Testing direct email sending...')
            
            html_content = template.html_content.replace('{{content}}', campaign.content)
            
            email = EmailMultiAlternatives(
                subject=campaign.subject,
                body='This is a test email',
                from_email=f"{sender_email.sender_name} <{sender_email.email}>",
                to=[test_email],
                reply_to=[sender_email.reply_to] if sender_email.reply_to else None
            )
            email.attach_alternative(html_content, "text/html")
            
            email.send()
            
            self.stdout.write(self.style.SUCCESS(f'Test email sent successfully to {test_email}'))
            
            # Test campaign sending
            self.stdout.write('Testing campaign sending...')
            campaign.status = Campaign.STATUS_SENDING
            campaign.save()
            
            # Call the send method
            from apps.campaigns.views import CampaignViewSet
            viewset = CampaignViewSet()
            viewset._send_sync(campaign)
            
            self.stdout.write(self.style.SUCCESS('Campaign sending test completed'))
            
            # Show results
            self.stdout.write(f'Campaign status: {campaign.get_status_display()}')
            self.stdout.write(f'Emails sent: {campaign.emails_sent}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc()) 