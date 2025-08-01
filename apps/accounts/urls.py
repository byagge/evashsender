from django.urls import path
from .views import (
    RegisterView, 
    ActivateView, 
    EmailSentView, 
    ResendEmailView,
    LoginView, 
    LogoutView,
    ProfileUpdateAPIView,
    PasswordChangeAPIView,
    PurchasedPlanListAPIView,
    DeleteAccountAPIView, 
    account_settings_page,
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView
)
app_name = 'accounts'

urlpatterns = [
    path('signup/', RegisterView.as_view(), name='signup'),
    path('activate/<uidb64>/<token>/', ActivateView.as_view(), name='activate'),
    path('email/sent/', EmailSentView.as_view(), name='email_sent'),
    path('email/resend/', ResendEmailView.as_view(), name='resend_email'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('api/account/profile/',     ProfileUpdateAPIView.as_view(),    name='api-profile'),
    path('api/account/password/',    PasswordChangeAPIView.as_view(),   name='api-password-change'),
    path('api/account/plans/',       PurchasedPlanListAPIView.as_view(), name='api-plans'),
    path('api/account/delete/',      DeleteAccountAPIView.as_view(),    name='api-delete-account'),
    path('settings/', account_settings_page, name='account_settings'),
    
    # Password Reset URLs
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password_reset/complete/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
