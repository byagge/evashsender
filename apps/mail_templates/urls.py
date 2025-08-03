# core/apps/mail_templates/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailTemplateViewSet, TemplateImageViewSet, TemplateSpaView, ImageUploadView

router = DefaultRouter()
router.register(r'templates', EmailTemplateViewSet, basename='templates')
router.register(r'images', TemplateImageViewSet, basename='images')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/upload-image/', ImageUploadView.as_view(), name='upload_image'),
    path('', TemplateSpaView.as_view(), name='templates_spa'),
]
