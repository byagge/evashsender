# mailer/serializers.py

from rest_framework import serializers
from .models import ContactList, Contact

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'email', 'status', 'added_date']

class ContactListSerializer(serializers.ModelSerializer):
    # убираем source=… — DRF найдёт total_contacts, valid_count и т.д. по name
    total_contacts    = serializers.IntegerField(read_only=True)
    valid_count       = serializers.IntegerField(read_only=True)
    invalid_count     = serializers.IntegerField(read_only=True)
    blacklisted_count = serializers.IntegerField(read_only=True)
    contacts          = ContactSerializer(many=True, read_only=True)

    class Meta:
        model = ContactList
        fields = [
            'id', 'name', 'created_at', 'updated_at',
            'total_contacts', 'valid_count', 'invalid_count', 'blacklisted_count',
            'contacts',
        ]
