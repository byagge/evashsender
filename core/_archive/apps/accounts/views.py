from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.mail import send_mail
import re

from .models import User

from django.shortcuts   import redirect, render
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .utils            import get_email_provider

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.db import IntegrityError

from .models import User

class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        name            = request.POST.get('name','').strip()
        email           = request.POST.get('email','').strip().lower()
        password        = request.POST.get('password','')
        confirm         = request.POST.get('confirmPassword','')
        terms_accepted  = 'terms' in request.POST

        errors = {}
        # Повторная валидация
        if len(name) < 3:
            errors['name'] = 'Имя должно быть не менее 3 символов'
        if '@' not in email or '.' not in email:
            errors['email'] = 'Неверный формат email'
        if len(password) < 8:
            errors['password'] = 'Пароль минимум 8 символов'
        if password != confirm:
            errors['confirmPassword'] = 'Пароли не совпадают'
        if not terms_accepted:
            errors['terms'] = 'Нужно согласиться с условиями'

        if User.objects.filter(email=email).exists():
            errors['email'] = 'Email уже зарегистрирован'
    
        if errors:
            return render(request, self.template_name, {
                'errors': errors,
                'data': request.POST
            })

        # Создаём пользователя в неактивном режиме
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                full_name=name,
                is_active=True
            )
        except IntegrityError:
            messages.error(request, 'Не удалось создать аккаунт. Попробуйте позже.')
            return redirect('accounts:signup')

        # Генерируем токен и отправляем письмо
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link  = request.build_absolute_uri(
            reverse('accounts:activate', args=[uid, token])
        )
        send_mail(
            'Подтвердите ваш Email',
            f'Чтобы активировать аккаунт, перейдите по ссылке: {link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=f'<p><a href="{link}">Подтвердить Email</a></p>'
        )

        # Входим сразу (активируем после подтверждения почты)
        login(request, user, backend='apps.accounts.middleware.EmailBackend')
        return redirect('accounts:email_sent')


class EmailSentView(LoginRequiredMixin, View):
    login_url = 'accounts:login'
    redirect_field_name = None

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'is_email_verified', False):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        email = request.user.email
        provider = get_email_provider(email)

        context = {
            'email': email,
            # если provider None — ключей name/url не будет
            **({'provider_name': provider['name'], 'provider_url': provider['url']} if provider else {})
        }
        return render(request, 'email_sent.html', context)

class ActivateView(View):
    def get(self, request, uidb64, token):
        try:
            uid  = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            user = None
        if user and default_token_generator.check_token(user, token):
            user.is_active = True
            user.is_email_verified = True
            user.save()
            login(request, user, backend='apps.accounts.middleware.EmailBackend')
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, 'account/verification_invalid.html')


from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.views import View
from django.conf import settings

template_name = 'login.html'

class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email','').strip().lower()
        password = request.POST.get('password','')
        remember = request.POST.get('remember') == 'on'

        data = {'email': email, 'remember': remember}
        errors = {}
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Неверный формат email'
        if not password:
            errors['password'] = 'Пароль не может быть пустым'

        if not errors:
            user = authenticate(request, username=email, password=password)
            if user is None:
                errors['non_field'] = 'Неверный email или пароль'
            else:
                login(request, user, backend='apps.accounts.backends.EmailBackend')
                if remember:
                    request.session.set_expiry(60*60*24*30*6)
                # После логина перенаправляем на верификацию, если не подтвердил email
                if not user.is_email_verified:
                    return redirect('accounts:email_sent')
                # Получаем next параметр из URL или используем dashboard по умолчанию
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)

        return render(request, self.template_name, {'errors': errors, 'data': data})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(settings.LOGOUT_REDIRECT_URL)
    


from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import PurchasedPlan
from .serializers import (
    ProfileSerializer, 
    PasswordChangeSerializer,
    PurchasedPlanSerializer
)

User = get_user_model()

class ProfileUpdateAPIView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = ProfileSerializer

    def get_object(self):
        return self.request.user

class PasswordChangeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = PasswordChangeSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"detail": "Пароль успешно изменён"}, status=status.HTTP_200_OK)

class PurchasedPlanListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = PurchasedPlanSerializer

    def get_queryset(self):
        return PurchasedPlan.objects.filter(user=self.request.user).order_by('-start_date')

class DeleteAccountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = PasswordChangeSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.delete()
        return Response({"detail": "Аккаунт удалён"}, status=status.HTTP_204_NO_CONTENT)

# apps/accounts/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def account_settings_page(request):
    # Просто отдаём шаблон — всё остальное (данные пользователя, планы и т.п.)
    # берётся прямо в JS через REST API
    return render(request, 'settings.html')
