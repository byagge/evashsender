# core/apps/emails/views.py

from django.conf import settings
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db import IntegrityError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import uuid
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import SenderEmail, Domain
from .serializers import SenderEmailSerializer

import uuid
import dns.resolver

from .models import Domain, SenderEmail
from .serializers import DomainSerializer, SenderEmailSerializer
from .utils import has_spf, has_dkim, validate_spf_record

class DomainViewSet(viewsets.ModelViewSet):
    serializer_class   = DomainSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Domain.objects.filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        token = uuid.uuid4().hex
        serializer.save(owner=self.request.user, verification_token=token)

    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        domain = self.get_object()
        
        # SPF проверка с использованием утилиты
        spf_ok = has_spf(domain.domain_name)
        
        # DKIM проверка с использованием утилиты
        dkim_ok = has_dkim(domain.domain_name, selector='ep1')
        
        print(f"Domain {domain.domain_name}: SPF={spf_ok}, DKIM={dkim_ok}")  # Отладка
        
        domain.spf_verified = spf_ok
        domain.dkim_verified = dkim_ok
        domain.is_verified = spf_ok and dkim_ok
        domain.save(update_fields=['spf_verified', 'dkim_verified', 'is_verified'])
        
        return Response(DomainSerializer(domain).data)


class SenderEmailViewSet(viewsets.ModelViewSet):
    """
    Создаём отправителя (sender email) со следующей логикой:
     - из email вытягиваем домен
     - проверяем, что Domain с таким name есть у пользователя
     - если нет — 400 с подсказкой добавить домен
     - если есть, но не подтверждён — 400 с подсказкой подтвердить домен
     - иначе создаём запись SenderEmail, генерируем токен и шлём письмо-подтверждение
    """
    serializer_class = SenderEmailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Возвращаем все email'ы пользователя
        return SenderEmail.objects.filter(
            owner=self.request.user
        ).select_related('domain')

    @action(detail=False, methods=['get'], url_path='verified')
    def verified(self, request):
        """
        GET /emails/api/emails/verified/
        Возвращает только подтвержденные email'ы для использования в кампаниях
        """
        # Получаем только подтвержденные
        verified_emails = SenderEmail.objects.filter(
            owner=request.user,
            is_verified=True
        ).select_related('domain')
        
        # Сериализуем и возвращаем результат
        serializer = self.get_serializer(verified_emails, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        email_addr = request.data.get('email', '').strip().lower()
        if '@' not in email_addr:
            return Response({'email': 'Неверный формат email.'},
                            status=status.HTTP_400_BAD_REQUEST)

        domain_part = email_addr.split('@', 1)[1]
        # 1) Домен должен существовать и принадлежать текущему пользователю
        try:
            domain_obj = Domain.objects.get(owner=request.user,
                                            domain_name=domain_part)
        except Domain.DoesNotExist:
            return Response(
                {'detail': f'Домен {domain_part} не найден. Сначала добавьте и подтвердите домен.'},
                status=status.HTTP_400_BAD_REQUEST)

        # 2) Домен должен быть верифицирован
        if not domain_obj.is_verified:
            return Response(
                {'detail': f'Домен {domain_part} ещё не подтверждён. Перейдите в раздел «Домены» и завершите верификацию.'},
                status=status.HTTP_400_BAD_REQUEST)

        # 3) Всё ок — создаём отправителя и шлём письмо
        try:
            token = uuid.uuid4().hex
            sender = SenderEmail.objects.create(
                owner=request.user,
                email=email_addr,
                domain=domain_obj,
                verification_token=token
            )

            # Отправляем письмо-подтверждение
            confirm_url = request.build_absolute_uri(
                f"/emails/confirm-sender/?token={token}"
            )
            send_mail(
                subject="Подтверждение отправителя",
                message=f"Пожалуйста, подтвердите ваш адрес: {confirm_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_addr],
                fail_silently=False,
            )

            return Response(
                SenderEmailSerializer(sender).data,
                status=status.HTTP_201_CREATED
            )
        except IntegrityError:
            return Response(
                {"detail": "Этот email уже добавлен."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def resend(self, request, pk=None):
        """
        POST /emails/api/emails/{pk}/resend/
        Повторно шлёт письмо-подтверждение, если ещё не верифицировано.
        """
        sender = self.get_object()

        if sender.is_verified:
            return Response(
                {"detail": "Этот email уже подтверждён."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Собираем ссылку подтверждения
        confirm_url = request.build_absolute_uri(
            f"/emails/confirm-sender/?token={sender.verification_token}"
        )

        send_mail(
            subject="Подтверждение отправителя (повторное)",
            message=f"Пожалуйста, подтвердите ваш адрес по ссылке:\n\n{confirm_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[sender.email],
            fail_silently=False,
        )

        return Response({"detail": "Письмо с подтверждением отправлено повторно."})

from django.shortcuts import redirect, get_object_or_404
from django.views import View

class SenderConfirmView(View):
    def get(self, request):
        token = request.GET.get('token')
        sender = get_object_or_404(SenderEmail, verification_token=token)
        sender.is_verified = True
        sender.verified_at = timezone.now()
        sender.save(update_fields=['is_verified','verified_at'])
        # после подтверждения можно редиректить на SPA с параметром ?confirmed=yes
        return redirect(f"/emails/?confirmed=1")

class EmailPlatformSpaView(LoginRequiredMixin, TemplateView):
    """
    Единая SPA-страница, где через Alpine.js переключаются 
    табы Emails ↔ Domains
    """
    template_name = 'domains.html'
