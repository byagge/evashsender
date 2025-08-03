from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('pricing/', views.pricing_page, name='pricing'),
    path('api/plans/', views.get_plans_api, name='get_plans_api'),
    path('purchase/confirm/', views.purchase_confirmation_page, name='purchase_confirmation'),
    path('purchase/success/', views.purchase_success, name='purchase_success'),
] 