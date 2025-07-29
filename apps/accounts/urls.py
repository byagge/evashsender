from django.urls import path
from .views import RegisterView, ActivateView, EmailSentView, LoginView, LogoutView
from django.urls import path
from .views import (
    ProfileUpdateAPIView,
    PasswordChangeAPIView,
    PurchasedPlanListAPIView,
    DeleteAccountAPIView, account_settings_page
)
app_name = 'accounts'

urlpatterns = [
    path('signup/', RegisterView.as_view(), name='signup'),
    path('activate/<uidb64>/<token>/', ActivateView.as_view(), name='activate'),
    path('email/sent/', EmailSentView.as_view(), name='email_sent'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/account/profile/',     ProfileUpdateAPIView.as_view(),    name='api-profile'),
    path('api/account/password/',    PasswordChangeAPIView.as_view(),   name='api-password-change'),
    path('api/account/plans/',       PurchasedPlanListAPIView.as_view(), name='api-plans'),
    path('api/account/delete/',      DeleteAccountAPIView.as_view(),    name='api-delete-account'),
    path('settings/', account_settings_page, name='account_settings'),
]
