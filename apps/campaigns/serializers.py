# core/apps/campaigns/serializers.py

from rest_framework import serializers

from apps.emails.models import SenderEmail
from apps.mailer.models import ContactList
from apps.mail_templates.models import EmailTemplate
from .models import Campaign, CampaignStats, EmailTracking

class EmailTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTracking
        fields = ['id', 'tracking_id', 'sent_at', 'opened_at', 'clicked_at', 'bounced_at', 'bounce_reason']

class CampaignStatsSerializer(serializers.ModelSerializer):
    emails_sent = serializers.SerializerMethodField()
    opens_count = serializers.SerializerMethodField()
    clicks_count = serializers.SerializerMethodField()
    bounces_count = serializers.SerializerMethodField()

    class Meta:
        model = CampaignStats
        fields = ['emails_sent', 'opens_count', 'clicks_count', 'bounces_count']

    def get_emails_sent(self, obj):
        return EmailTracking.objects.filter(
            campaign=obj.campaign,
            contact__in=obj.contact_list.contacts.all()
        ).count()

    def get_opens_count(self, obj):
        return EmailTracking.objects.filter(
            campaign=obj.campaign,
            contact__in=obj.contact_list.contacts.all(),
            opened_at__isnull=False
        ).count()

    def get_clicks_count(self, obj):
        return EmailTracking.objects.filter(
            campaign=obj.campaign,
            contact__in=obj.contact_list.contacts.all(),
            clicked_at__isnull=False
        ).count()

    def get_bounces_count(self, obj):
        return EmailTracking.objects.filter(
            campaign=obj.campaign,
            contact__in=obj.contact_list.contacts.all(),
            bounced_at__isnull=False
        ).count()

class CampaignSerializer(serializers.ModelSerializer):
    # Используем обычные поля для записи
    sender_email = serializers.PrimaryKeyRelatedField(
        queryset=SenderEmail.objects.all(),
        required=False,
        allow_null=True
    )
    contact_lists = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ContactList.objects.all(),
        required=False,
        allow_empty=True
    )
    template = serializers.PrimaryKeyRelatedField(
        queryset=EmailTemplate.objects.all(),
        required=False,
        allow_null=True
    )

    # Эти поля оставляем как read-only для отображения доп. данных
    contact_lists_detail = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    emails_sent = serializers.SerializerMethodField()
    delivered_emails = serializers.SerializerMethodField()
    open_rate = serializers.SerializerMethodField()
    click_rate = serializers.SerializerMethodField()
    bounce_rate = serializers.SerializerMethodField()
    delivery_rate = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'template', 'sender_email', 'subject',
            'content', 'contact_lists', 'contact_lists_detail',
            'scheduled_at', 'status', 'status_display', 'created_at', 'sent_at', 'updated_at',
            'auto_send_at', 'stats', 'emails_sent', 'delivered_emails', 
            'open_rate', 'click_rate', 'bounce_rate', 'delivery_rate',
            'sender_name', 'reply_to'
        ]
        read_only_fields = ['id', 'status', 'status_display', 'created_at', 'sent_at', 'updated_at', 'auto_send_at']

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_sender_name(self, obj):
        return obj.sender_email.sender_name if obj.sender_email else ''

    def get_reply_to(self, obj):
        return obj.sender_email.reply_to if obj.sender_email else ''

    def validate(self, data):
        # Для черновиков проверяем только наличие хотя бы одного поля
        if (self.instance and self.instance.status == Campaign.STATUS_DRAFT) or not self.instance:
            # Проверяем, что хотя бы одно поле заполнено
            has_any_field = any(
                data.get(field) for field in ['name', 'template', 'sender_email', 'subject', 'content', 'contact_lists']
            )
            if not has_any_field:
                raise serializers.ValidationError('При сохранении черновика должно быть заполнено хотя бы одно поле')
            return data

        # Полная валидация перед отправкой
        required_fields = ['name', 'template', 'sender_email', 'subject', 'content', 'contact_lists']
        for field in required_fields:
            if field not in data:
                # Если поле не в данных, используем значение из instance
                if not getattr(self.instance, field, None):
                    raise serializers.ValidationError({field: f'Поле {field} обязательно'})
            elif not data[field]:
                raise serializers.ValidationError({field: f'Поле {field} обязательно'})

        return data

    def get_contact_lists_detail(self, obj):
        return [
            {
                'id': str(cl.id),
                'name': cl.name,
                'contacts_count': cl.contacts.count()
            }
            for cl in obj.contact_lists.all()
        ]

    def get_stats(self, obj):
        return CampaignStatsSerializer(obj.stats.all(), many=True).data

    def get_emails_sent(self, obj):
        return obj.emails_sent

    def get_delivered_emails(self, obj):
        return obj.delivered_emails

    def get_open_rate(self, obj):
        return obj.open_rate

    def get_click_rate(self, obj):
        return obj.click_rate

    def get_bounce_rate(self, obj):
        return obj.bounce_rate

    def get_delivery_rate(self, obj):
        return obj.delivery_rate
