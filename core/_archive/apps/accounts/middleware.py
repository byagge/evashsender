from core.settings import base as settings
from django.shortcuts import redirect
from django.urls import reverse

class EmailVerificationMiddleware:
    """
    Если настройка REQUIRE_EMAIL_VERIFICATION=True,
    перенаправляет неподтверждённых пользователей на страницу email_sent
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        path = request.path
        exempt = [reverse('accounts:email_sent'), reverse('accounts:signup'), '/accounts/activate/']
        if user.is_authenticated and not user.is_email_verified and settings.REQUIRE_EMAIL_VERIFICATION:
            if not any(path.startswith(e) for e in exempt):
                return redirect('accounts:email_sent')
        return self.get_response(request)

