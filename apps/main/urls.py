from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('pricing/', views.pricing, name='pricing'),
    path('purchase/confirm/', views.purchase_confirmation, name='purchase_confirmation'),
    path('purchase/success/', views.purchase_success, name='purchase_success'),
] 