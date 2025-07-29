from django.urls import path
from . import views

app_name = 'moderation'

urlpatterns = [
    path('', views.moderation_dashboard, name='dashboard'),
    path('campaign/<uuid:campaign_id>/approve/', views.approve_campaign, name='approve_campaign'),
    path('campaign/<uuid:campaign_id>/reject/', views.reject_campaign, name='reject_campaign'),
    path('user/<int:user_id>/trust/', views.mark_trusted_user, name='mark_trusted_user'),
    path('search/', views.search_campaigns, name='search_campaigns'),
] 