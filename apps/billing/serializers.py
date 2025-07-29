from rest_framework import serializers
from .models import PlanType, Plan, PurchasedPlan, BillingSettings


class PlanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanType
        fields = ['id', 'name', 'description', 'is_active']


class PlanSerializer(serializers.ModelSerializer):
    plan_type = PlanTypeSerializer(read_only=True)
    final_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Plan
        fields = [
            'id', 'title', 'plan_type', 'subscribers', 'emails_per_month',
            'max_emails_per_day', 'price', 'discount', 'final_price',
            'is_active', 'is_featured', 'sort_order'
        ]
    
    def get_final_price(self, obj):
        return float(obj.get_final_price())


class PurchasedPlanSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchasedPlan
        fields = [
            'id', 'plan', 'start_date', 'end_date', 'is_active',
            'auto_renew', 'payment_method', 'transaction_id', 'amount_paid',
            'days_remaining', 'is_expired', 'created_at'
        ]
    
    def get_days_remaining(self, obj):
        return obj.days_remaining()
    
    def get_is_expired(self, obj):
        return obj.is_expired()


class BillingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingSettings
        fields = [
            'free_plan_subscribers', 'free_plan_emails', 'free_plan_daily_limit',
            'currency', 'tax_rate'
        ]


class UserPlanInfoSerializer(serializers.Serializer):
    """Информация о текущем плане пользователя"""
    current_plan = PlanSerializer()
    plan_expiry = serializers.DateTimeField()
    emails_sent_today = serializers.IntegerField()
    has_exceeded_daily_limit = serializers.BooleanField()
    days_remaining = serializers.IntegerField()
    is_plan_expired = serializers.BooleanField() 