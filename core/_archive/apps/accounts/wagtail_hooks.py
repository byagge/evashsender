from wagtail import hooks
from apps.accounts.utils import CustomUserViewSet

@hooks.register("register_admin_viewset")
def register_custom_user_viewset():
    return CustomUserViewSet("users", url_prefix="users")