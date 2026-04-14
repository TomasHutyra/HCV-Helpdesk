from .models import UserRole


def user_roles(request):
    """Přidá role přihlášeného uživatele do kontextu šablon."""
    if not request.user.is_authenticated:
        return {}
    roles = set(request.user.user_roles.values_list('role', flat=True))
    return {
        'user_roles': roles,
        'is_requester': UserRole.REQUESTER in roles,
        'is_resolver': UserRole.RESOLVER in roles,
        'is_sales': UserRole.SALES in roles,
        'is_manager': UserRole.MANAGER in roles,
        'is_hcv_admin': UserRole.ADMIN in roles,
    }
