# core/apps/mail_templates/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmailTemplateViewSet, TemplateSpaView

router = DefaultRouter()
router.register(r'templates', EmailTemplateViewSet, basename='templates')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', TemplateSpaView.as_view(), name='templates_spa'),
]
