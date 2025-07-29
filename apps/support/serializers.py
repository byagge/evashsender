from rest_framework import serializers
from .models import SupportTicket, SupportMessage, SupportAttachment

class SupportTicketListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'ticket_id', 'ticket_subject', 'ticket_description', 'ticket_status', 'ticket_priority',
            'ticket_category', 'ticket_user', 'ticket_assigned_to',
            'ticket_created_at', 'ticket_updated_at', 'ticket_resolved_at', 'ticket_closed_at'
        ]

class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ['ticket_subject', 'ticket_description', 'ticket_category', 'ticket_priority']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['ticket_user'] = request.user
        ticket = super().create(validated_data)
        # Создаём первое сообщение с текстом описания тикета
        SupportMessage.objects.create(
            message_ticket=ticket,
            message_author=request.user,
            message_text=ticket.ticket_description
        )
        return ticket

class SupportTicketDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'ticket_id', 'ticket_subject', 'ticket_description', 'ticket_status', 'ticket_priority',
            'ticket_category', 'ticket_user', 'ticket_assigned_to',
            'ticket_created_at', 'ticket_updated_at', 'ticket_resolved_at', 'ticket_closed_at'
        ]

class SupportMessageSerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()
    class Meta:
        model = SupportMessage
        fields = [
            'message_id', 'message_text', 'message_author', 'message_internal', 'message_staff_reply',
            'message_created_at', 'message_updated_at', 'attachment_url'
        ]
    def get_attachment_url(self, obj):
        attachment = obj.message_attachments.first()
        if attachment and attachment.attachment_file:
            return attachment.attachment_file.url
        return None

class SupportMessageCreateSerializer(serializers.ModelSerializer):
    attachment = serializers.FileField(required=False, write_only=True)
    class Meta:
        model = SupportMessage
        fields = ['message_text', 'message_internal', 'attachment']

    def create(self, validated_data):
        request = self.context.get('request')
        attachment_file = validated_data.pop('attachment', None)
        if request and hasattr(request, 'user'):
            validated_data['message_author'] = request.user
        message = super().create(validated_data)
        if attachment_file:
            SupportAttachment = self.Meta.model._meta.apps.get_model('support', 'SupportAttachment')
            SupportAttachment.objects.create(
                attachment_message=message,
                attachment_ticket=message.message_ticket,
                attachment_file=attachment_file,
                attachment_filename=attachment_file.name,
                attachment_file_size=attachment_file.size,
                attachment_mime_type=attachment_file.content_type
            )
        return message 