# core/apps/mail_templates/views.py

from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EmailTemplate
from .serializers import EmailTemplateSerializer


# mail_templates/views.py

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import EmailTemplate
from .serializers import EmailTemplateSerializer

class EmailTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmailTemplate.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception:
            return Response(
                {"detail": "Шаблон с таким названием уже существует."},
                status=status.HTTP_400_BAD_REQUEST
            )


class TemplateSpaView(LoginRequiredMixin, TemplateView):
    """
    Отдаёт SPA-шаблон (index.html с Alpine.js и <script>).
    """
    template_name = "templates.html"
