from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.decorators import login_required
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
import re

from .models import User
from .utils import get_email_provider
from apps.billing.models import PurchasedPlan
from .serializers import (
    ProfileSerializer, 
    PasswordChangeSerializer,
    PurchasedPlanSerializer
)

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
        # Рендерим красивый HTML шаблон
        from django.template.loader import render_to_string
        html_message = render_to_string('email_verification.html', {
            'user': user,
            'activation_link': link,
            'protocol': 'https' if request.is_secure() else 'http',
            'domain': request.get_host(),
        })
        
        send_mail(
            'Подтвердите ваш Email - vashsender',
            f'Чтобы активировать аккаунт, перейдите по ссылке: {link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message
        )

        # Входим сразу (активируем после подтверждения почты)
        login(request, user, backend='apps.accounts.backends.EmailBackend')
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
            'provider': provider
        }
        return render(request, 'email_sent.html', context)


class ResendEmailView(LoginRequiredMixin, View):
    login_url = 'accounts:login'
    redirect_field_name = None

    def post(self, request):
        user = request.user
        if getattr(user, 'is_email_verified', False):
            return redirect('home')

        # Генерируем новый токен и отправляем письмо
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link  = request.build_absolute_uri(
            reverse('accounts:activate', args=[uid, token])
        )
        
        try:
            # Рендерим красивый HTML шаблон
            from django.template.loader import render_to_string
            html_message = render_to_string('email_verification.html', {
                'user': user,
                'activation_link': link,
                'protocol': 'https' if request.is_secure() else 'http',
                'domain': request.get_host(),
            })
            
            send_mail(
                'Подтвердите ваш Email - vashsender',
                f'Чтобы активировать аккаунт, перейдите по ссылке: {link}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message
            )
            messages.success(request, 'Письмо отправлено повторно!')
        except Exception as e:
            messages.error(request, 'Не удалось отправить письмо. Попробуйте позже.')
        
        return redirect('accounts:email_sent')


class ActivateView(View):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_email_verified = True
            user.save()
            messages.success(request, 'Email подтвержден! Теперь вы можете использовать все функции.')
            login(request, user, backend='apps.accounts.backends.EmailBackend')
            return redirect('home')
        else:
            messages.error(request, 'Недействительная ссылка для активации.')
            return redirect('accounts:login')


class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name)

    def post(self, request):
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        remember = 'remember' in request.POST

        errors = {}
        if not email:
            errors['email'] = 'Введите email'
        if not password:
            errors['password'] = 'Введите пароль'

        if errors:
            return render(request, self.template_name, {
                'errors': errors,
                'data': request.POST
            })

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user, backend='apps.accounts.backends.EmailBackend')
            if not remember:
                request.session.set_expiry(0)
            return redirect('home')
        else:
            errors['non_field'] = 'Неверный email или пароль'
            return render(request, self.template_name, {
                'errors': errors,
                'data': request.POST
            })


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, 'Вы успешно вышли из аккаунта.')
        return redirect('home')


# Password Reset Views
class CustomPasswordResetView(PasswordResetView):
    template_name = 'password_reset.html'
    email_template_name = 'password_reset_email.txt'
    html_email_template_name = 'password_reset_email.html'
    subject_template_name = 'password_reset_subject.txt'
    success_url = '/accounts/password_reset/done/'
    
    def form_valid(self, form):
        email = form.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            if not user.is_email_verified:
                messages.error(self.request, 'Сначала подтвердите ваш email адрес.')
                return self.form_invalid(form)
        except User.DoesNotExist:
            messages.error(self.request, 'Пользователь с таким email не найден.')
            return self.form_invalid(form)
        
        return super().form_valid(form)
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Переопределяем метод отправки для поддержки HTML писем
        """
        from django.template.loader import render_to_string
        from django.core.mail import EmailMultiAlternatives
        
        subject = render_to_string(subject_template_name, context)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        
        # Рендерим текстовую версию
        text_message = render_to_string(email_template_name, context)
        
        # Рендерим HTML версию
        html_message = render_to_string(html_email_template_name, context)
        
        # Создаем письмо с альтернативными версиями
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_message, "text/html")
        email.send()


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'password_reset_confirm.html'
    success_url = '/accounts/password_reset/complete/'


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'password_reset_complete.html'

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

@login_required
def account_settings_page(request):
    # Просто отдаём шаблон — всё остальное (данные пользователя, планы и т.п.)
    # берётся прямо в JS через REST API
    return render(request, 'settings.html')
