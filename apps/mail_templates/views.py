# core/apps/mail_templates/views.py

from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from PIL import Image
import io
import os

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser

from .models import EmailTemplate, TemplateImage
from .serializers import EmailTemplateSerializer, TemplateImageSerializer


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


class TemplateImageViewSet(viewsets.ModelViewSet):
    """ViewSet для управления изображениями шаблонов"""
    serializer_class = TemplateImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return TemplateImage.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def gallery(self, request):
        """Возвращает галерею изображений пользователя"""
        images = self.get_queryset()
        serializer = self.get_serializer(images, many=True)
        return Response(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class ImageUploadView(LoginRequiredMixin, TemplateView):
    """Представление для загрузки изображений через CKEditor"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Получаем загруженный файл
            uploaded_file = request.FILES.get('upload')
            if not uploaded_file:
                return JsonResponse({
                    'error': {
                        'message': 'Файл не найден'
                    }
                }, status=400)

            # Проверяем тип файла
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if uploaded_file.content_type not in allowed_types:
                return JsonResponse({
                    'error': {
                        'message': 'Неподдерживаемый тип файла. Разрешены только: JPEG, PNG, GIF, WebP'
                    }
                }, status=400)

            # Проверяем размер файла (максимум 10 МБ)
            max_size = 10 * 1024 * 1024  # 10 МБ
            if uploaded_file.size > max_size:
                return JsonResponse({
                    'error': {
                        'message': 'Файл слишком большой. Максимальный размер: 10 МБ'
                    }
                }, status=400)

            # Открываем изображение для получения размеров
            try:
                with Image.open(uploaded_file) as img:
                    width, height = img.size
            except Exception:
                width, height = None, None

            # Создаем объект TemplateImage
            template_image = TemplateImage.objects.create(
                owner=request.user,
                image=uploaded_file,
                filename=uploaded_file.name,
                file_size=uploaded_file.size,
                width=width,
                height=height
            )

            # Возвращаем URL изображения для CKEditor
            image_url = request.build_absolute_uri(template_image.image.url)
            
            return JsonResponse({
                'url': image_url,
                'uploaded': True,
                'fileName': uploaded_file.name
            })

        except Exception as e:
            return JsonResponse({
                'error': {
                    'message': f'Ошибка при загрузке: {str(e)}'
                }
            }, status=500)


class TemplateSpaView(LoginRequiredMixin, TemplateView):
    """
    Отдаёт SPA-шаблон (index.html с Alpine.js и <script>).
    """
    template_name = "templates.html"
