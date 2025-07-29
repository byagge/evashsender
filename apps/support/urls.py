from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupportTicketViewSet, SupportMessageViewSet, SupportTicketListView, SupportAdminPanelView

router = DefaultRouter()
router.register(r'tickets', SupportTicketViewSet, basename='support-ticket')

urlpatterns = [
    path('', SupportTicketListView.as_view(), name='ticket-list'),
    path('admin/', SupportAdminPanelView.as_view(), name='support-admin-panel'),
    path('api/', include(router.urls)),
] 