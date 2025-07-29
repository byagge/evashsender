from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactListViewSet, ListSpaView

router = DefaultRouter()
router.register(r'contactlists', ContactListViewSet, basename='contactlists')

urlpatterns = [
    path('api/', include(router.urls)),
    path('', ListSpaView.as_view(), name='lists_spa'),
]
