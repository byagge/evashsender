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
router.register(r'campaigns', views.CampaignViewSet, basename='campaign')

urlpatterns = [
    path('api/', include(router.urls)),
    path('campaigns/', views.CampaignListView.as_view(), name='campaign_list'),
    path('campaigns/create/', views.CampaignFormView.as_view(), name='campaign_create'),
    path('campaigns/<uuid:pk>/edit/', views.CampaignFormView.as_view(), name='campaign_edit'),
    path('campaigns/<uuid:campaign_id>/track-open/', views.track_email_open, name='track_email_open'),
    path('campaigns/<uuid:campaign_id>/track-click/', views.track_email_click, name='track_email_click'),
]
