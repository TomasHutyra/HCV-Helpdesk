from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext as _


def role_required(*roles):
    """Dekorátor pro views — přístup pouze pro uživatele s danou rolí."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if not request.user.has_role(*roles):
                messages.error(request, _('Nemáte oprávnění pro tuto akci.'))
                return redirect('tickets:list')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def login_required_simple(view_func):
    """Jednoduchý login required bez next parametru."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
