from rest_framework import serializers
from .models import (
    PlanType, Plan, PurchasedPlan, BillingSettings
    # CloudPaymentsTransaction  # Временно отключено до применения миграций
)


class PlanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanType
        fields = ['id', 'name', 'description']


class PlanSerializer(serializers.ModelSerializer):
    plan_type = PlanTypeSerializer(read_only=True)
    final_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Plan
        fields = [
            'id', 'title', 'plan_type', 'subscribers', 'emails_per_month',
            'max_emails_per_day', 'price', 'discount', 'final_price',
            'is_featured', 'sort_order'
        ]
    
    def get_final_price(self, obj):
        return float(obj.get_final_price())


class PurchasedPlanSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    emails_remaining = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchasedPlan
        fields = [
            'id', 'plan', 'start_date', 'end_date', 'is_active',
            'auto_renew', 'payment_method', 'transaction_id',
            'amount_paid', 'emails_sent', 'emails_remaining',
            'days_remaining', 'is_expired', 'created_at'
        ]
    
    def get_emails_remaining(self, obj):
        return obj.get_emails_remaining()
    
    def get_days_remaining(self, obj):
        return obj.days_remaining()
    
    def get_is_expired(self, obj):
        return obj.is_expired()


# class CloudPaymentsTransactionSerializer(serializers.ModelSerializer):
#     plan = PlanSerializer(read_only=True)
#     
#     class Meta:
#         model = CloudPaymentsTransaction
#         fields = [
#             'id', 'plan', 'cloudpayments_id', 'amount', 'currency',
#             'status', 'payment_method', 'description', 'created_at',
#             'completed_at', 'card_last_four', 'card_type'
#         ]


class BillingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingSettings
        fields = [
            'free_plan_subscribers', 'free_plan_emails', 'free_plan_daily_limit',
            'cloudpayments_public_id', 'cloudpayments_test_mode',
            'auto_renewal_enabled', 'auto_renewal_days_before'
        ]


class UserPlanInfoSerializer(serializers.Serializer):
    has_plan = serializers.BooleanField()
    plan_name = serializers.CharField(allow_null=True)
    plan_type = serializers.CharField(allow_null=True)
    emails_limit = serializers.IntegerField(allow_null=True)
    emails_sent = serializers.IntegerField()
    emails_remaining = serializers.IntegerField()
    days_remaining = serializers.IntegerField()
    is_expired = serializers.BooleanField()
    emails_sent_today = serializers.IntegerField()
    has_exceeded_daily_limit = serializers.BooleanField() 