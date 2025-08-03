# core/apps/campaigns/serializers.py

from rest_framework import serializers

from apps.emails.models import SenderEmail
from apps.mailer.models import ContactList, Contact
from apps.mail_templates.models import EmailTemplate
from .models import Campaign, CampaignStats, EmailTracking

class EmailTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTracking
        fields = ['id', 'tracking_id', 'sent_at', 'opened_at', 'clicked_at', 'bounced_at', 'bounce_reason']

class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ['id', 'title', 'html_content']

class SenderEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SenderEmail
        fields = ['id', 'email', 'sender_name', 'reply_to']

class ContactListSerializer(serializers.ModelSerializer):
    contacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactList
        fields = ['id', 'name', 'contacts_count']
    
    def get_contacts_count(self, obj):
        return obj.contacts.count()

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'email', 'status', 'added_date']

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
    user = serializers.ReadOnlyField(source='user.email')
    template = serializers.PrimaryKeyRelatedField(queryset=EmailTemplate.objects.all(), required=False, allow_null=True)
    sender_email = serializers.PrimaryKeyRelatedField(queryset=SenderEmail.objects.all(), required=False, allow_null=True)
    sender_email_detail = SenderEmailSerializer(source='sender_email', read_only=True)
    contact_lists = serializers.PrimaryKeyRelatedField(queryset=ContactList.objects.all(), many=True, required=False)
    contact_lists_detail = serializers.SerializerMethodField()
    template_detail = EmailTemplateSerializer(source='template', read_only=True)
    recipients = ContactSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    emails_sent = serializers.ReadOnlyField()
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'user', 'name', 'subject', 'content', 'status', 'status_display',
            'created_at', 'updated_at', 'scheduled_at', 'sent_at',
            'template', 'template_detail', 'sender_email', 'sender_email_detail', 'contact_lists', 'contact_lists_detail', 'recipients',
            'emails_sent', 'open_rate', 'click_rate', 'celery_task_id', 'sender_name'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'sent_at']

    def validate(self, data):
        # Для черновиков проверяем только наличие хотя бы одного поля
        if (self.instance and self.instance.status == Campaign.STATUS_DRAFT) or not self.instance:
            # Проверяем, что хотя бы одно поле заполнено
            has_any_field = any(
                data.get(field) for field in ['name', 'template', 'sender_email', 'subject', 'content', 'contact_lists', 'sender_name']
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
        # Принудительно обновляем данные из базы
        obj.refresh_from_db()
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

    def to_representation(self, instance):
        # Принудительно обновляем данные из базы перед сериализацией
        try:
            instance.refresh_from_db()
        except Exception as e:
            # Если не удалось обновить, продолжаем с текущими данными
            pass
        return super().to_representation(instance)
