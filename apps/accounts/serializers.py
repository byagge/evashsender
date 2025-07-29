from rest_framework import serializers
from django.contrib.auth import get_user_model, password_validation
from apps.billing.models import PurchasedPlan

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['full_name']

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password     = serializers.CharField()

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value, self.context['request'].user)
        return value

class PurchasedPlanSerializer(serializers.ModelSerializer):
    plan = serializers.StringRelatedField()
    class Meta:
        model  = PurchasedPlan
        fields = ['plan', 'start_date', 'end_date', 'is_active']
