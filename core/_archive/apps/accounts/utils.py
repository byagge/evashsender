from wagtail.admin.viewsets.model import ModelViewSet
from apps.accounts.models import User
from core.utils.email_providers import EMAIL_PROVIDERS

class CustomUserViewSet(ModelViewSet):
    model = User
    icon = "user"
    add_to_admin_menu = False       # или True, если хотите, чтобы ссылка в меню добавилась вновь
    list_display = (
        "full_name",
        "email",
        "is_active",
    )
    filterset_fields = ("is_active",)
    ordering = ("full_name",)

    # ← Добавляем это:
    form_fields = [
        "email",
        "full_name",
        "is_email_verified",
        "is_active",
        "is_verified",
        "current_plan",
        "plan_expiry",
        "is_staff",
    ]

def get_email_provider(email: str) -> dict | None:
    """
    Если домен в EMAIL_PROVIDERS — возвращает {name, url},
    иначе — None.
    """
    domain = email.split('@')[-1].lower()
    return EMAIL_PROVIDERS.get(domain)
