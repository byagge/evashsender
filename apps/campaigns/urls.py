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
router.register(r'api/campaigns', views.CampaignViewSet, basename='campaign')

urlpatterns = [
    path('', views.CampaignListView.as_view(), name='campaign_list'),
    path('new/', views.CampaignFormView.as_view(), name='campaign_create'),
    path('<uuid:pk>/', views.CampaignFormView.as_view(), name='campaign_edit'),
    path('<uuid:campaign_id>/track-open/', views.track_email_open, name='track_email_open'),
    path('<uuid:campaign_id>/track-click/', views.track_email_click, name='track_email_click'),
    path('', include(router.urls)),
]
