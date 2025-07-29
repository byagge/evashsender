from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
import re
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

from .models import User
from .utils import get_email_provider


class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        name    = request.POST.get('name','').strip()
        email   = request.POST.get('email','').strip().lower()
        password = request.POST.get('password','')
        confirm  = request.POST.get('confirmPassword','')
        terms    = 'terms' in request.POST

        errors = {}
        if len(name) < 3:
            errors['name'] = 'Имя должно быть не менее 3 символов'
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Неверный формат email'
        if len(password) < 8:
            errors['password'] = 'Пароль минимум 8 символов'
        if password != confirm:
            errors['confirmPassword'] = 'Пароли не совпадают'
        if not terms:
            errors['terms'] = 'Нужно согласиться с условиями'
        if User.objects.filter(email=email).exists():
            errors['email'] = 'Email уже зарегистрирован'

        if errors:
            return render(request, self.template_name, {'errors': errors, 'data': request.POST})

        # Создаем пользователя активным, но с флагом is_email_verified=False
        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=name,
            is_active=True,
            is_email_verified=False
        )

        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        link  = request.build_absolute_uri(reverse('accounts:activate', args=[uid, token]))
        send_mail(
            'Подтвердите ваш Email',
            f'Чтобы активировать аккаунт, перейдите по ссылке: {link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=f'<p><a href="{link}">Подтвердить Email</a></p>'
        )

        # Логиним, перенаправляем на страницу с инструкцией
        login(request, user, backend='apps.accounts.backends.EmailBackend')
        return redirect('accounts:email_sent')


class EmailSentView(LoginRequiredMixin, View):
    login_url = 'accounts:login'
    redirect_field_name = None

    def dispatch(self, request, *args, **kwargs):
        # Если уже верифицирован, идем на домашнюю
        if request.user.is_email_verified:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        email = request.user.email
        provider = get_email_provider(email)
        context = {'email': email}
        if provider:
            context.update({'provider_name': provider['name'], 'provider_url': provider['url']})
        return render(request, 'email_sent.html', context)


class ActivateView(View):
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            user = None
        if user and default_token_generator.check_token(user, token):
            user.is_email_verified = True
            user.save()
            return redirect('home')
        return render(request, 'account/verification_invalid.html')


class LoginView(View):
    template_name = 'login.html'

    def get(self, request):
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
                return redirect(settings.LOGIN_REDIRECT_URL)

        return render(request, self.template_name, {'errors': errors, 'data': data})


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(settings.LOGOUT_REDIRECT_URL)


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
