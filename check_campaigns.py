#!/usr/bin/env python
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.campaigns.models import Campaign
from apps.mailer.models import ContactList, Contact
from apps.accounts.models import User

print("=== ПРОВЕРКА СИСТЕМЫ РАССЫЛОК ===")

# Проверяем пользователей
users = User.objects.all()
print(f"Пользователей: {users.count()}")
for user in users:
    print(f"  - {user.email} (ID: {user.id})")

# Проверяем кампании
campaigns = Campaign.objects.all()
print(f"\nКампаний: {campaigns.count()}")
for campaign in campaigns:
    print(f"  - {campaign.name} (ID: {campaign.id}, статус: {campaign.get_status_display()}, отправлено: {campaign.emails_sent})")
    print(f"    Пользователь: {campaign.user.email}")
    print(f"    Списки контактов: {list(campaign.contact_lists.all().values_list('name', flat=True))}")

# Проверяем списки контактов
contact_lists = ContactList.objects.all()
print(f"\nСписков контактов: {contact_lists.count()}")
for cl in contact_lists:
    contacts_count = cl.contacts.count()
    print(f"  - {cl.name} (ID: {cl.id}, контактов: {contacts_count})")
    print(f"    Владелец: {cl.owner.email}")

# Проверяем контакты
contacts = Contact.objects.all()
print(f"\nКонтактов: {contacts.count()}")
for contact in contacts:
    print(f"  - {contact.email} (ID: {contact.id})")

print("\n=== КОНЕЦ ПРОВЕРКИ ===") 