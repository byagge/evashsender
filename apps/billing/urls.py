from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'plan-types', views.PlanTypeViewSet)
router.register(r'plans', views.PlanViewSet)
router.register(r'purchased-plans', views.PurchasedPlanViewSet, basename='purchased-plan')
router.register(r'settings', views.BillingSettingsViewSet, basename='billing-settings')
router.register(r'user-plan-info', views.UserPlanInfoViewSet, basename='user-plan-info')

app_name = 'billing'

urlpatterns = [
    path('api/', include(router.urls)),
    # URLs для покупки тарифов
    path('confirm/', views.confirm_plan, name='confirm_plan'),
    path('activate-free/', views.activate_free_plan, name='activate_free_plan'),
    path('history/', views.plan_history, name='plan_history'),
    path('check-auth/', views.check_auth_status, name='check_auth_status'),
] 