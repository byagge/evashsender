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
        read_only_fields = fields

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
            'is_verified',
            'verification_token',
            'created_at',
            'verified_at'
        ]
        read_only_fields = fields

    def get_domain_name(self, obj):
        try:
            return obj.email.split('@')[1]
        except Exception:
            return None
