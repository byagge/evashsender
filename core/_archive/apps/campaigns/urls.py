# apps/campaigns/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

from .views import (
    CampaignViewSet,
    CampaignListView,
    CampaignFormView,
)

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')

urlpatterns = [
    # API routes: /campaigns/api/…
    path('api/', include(router.urls)),

    # UI
    # /campaigns/           — список
    path('', CampaignListView.as_view(), name='campaign_list'),
    # /campaigns/new/       — создание
    path('new/', CampaignFormView.as_view(), name='campaign_new'),
    # /campaigns/<uuid:pk>/  — редактирование
    path('<uuid:pk>/', CampaignFormView.as_view(), name='campaign_edit'),
    
    # Tracking endpoints
    path('<uuid:campaign_id>/track-open/', views.track_email_open, name='track_email_open'),
    path('<uuid:campaign_id>/track-click/', views.track_email_click, name='track_email_click'),
]
