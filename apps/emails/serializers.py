# core/apps/emails/serializers.py

from rest_framework import serializers
from .models import Domain, SenderEmail

class DomainSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    public_key = serializers.CharField(read_only=True)
    dkim_dns_record = serializers.SerializerMethodField()

    class Meta:
        model = Domain
        fields = [
            'id', 'owner', 'domain_name',
            'is_verified', 'spf_verified', 'dkim_verified',
            'verification_token', 'created_at',
            'public_key', 'dkim_dns_record',
        ]
        read_only_fields = [
            'id', 'owner', 'is_verified', 'spf_verified', 'dkim_verified',
            'verification_token', 'created_at', 'public_key',
        ]

    def validate_domain_name(self, value):
        if not value:
            raise serializers.ValidationError("Название домена не может быть пустым")
        
        # Убираем пробелы и приводим к нижнему регистру
        value = value.strip().lower()
        
        # Проверяем, что домен содержит точку (базовая валидация)
        if '.' not in value:
            raise serializers.ValidationError("Некорректный формат домена")
        
        # Проверяем, что домен не начинается и не заканчивается точкой
        if value.startswith('.') or value.endswith('.'):
            raise serializers.ValidationError("Некорректный формат домена")
        
        return value

    def get_dkim_dns_record(self, obj):
        return obj.dkim_dns_record


class SenderEmailSerializer(serializers.ModelSerializer):
    domain_name = serializers.SerializerMethodField()

    class Meta:
        model = SenderEmail
        fields = [
            'id',
            'email',
            'domain',
            'domain_name',
            'sender_name',
            'reply_to',
            'is_verified',
            'verification_token',
            'created_at',
            'verified_at'
        ]
        read_only_fields = [
            'id',
            'domain',
            'domain_name',
            'is_verified',
            'verification_token',
            'created_at',
            'verified_at'
        ]

    def get_domain_name(self, obj):
        try:
            return obj.email.split('@')[1]
        except Exception:
            return None
