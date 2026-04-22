from django.conf import settings
from django.contrib.auth.views import LoginView, PasswordChangeView as DjangoPasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.generic import ListView, CreateView, UpdateView, TemplateView

from .decorators import role_required
from .forms import LoginForm, UserCreateForm, UserUpdateForm, ProfileForm, CompanyForm, AreaForm
from .models import User, Company, UserRole
from apps.tickets.models import Area


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        # Nastavit jazyk uživatele přes cookie (Django 4.0+ — LANGUAGE_SESSION_KEY zrušen)
        lang = self.request.user.language
        translation.activate(lang)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
        return response


class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        # Aktualizovat jazyk po uložení přes cookie (Django 4.0+)
        lang = form.cleaned_data.get('language', 'cs')
        translation.activate(lang)
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang)
        messages.success(self.request, _('Profil byl uložen.'))
        return response


class PasswordChangeView(DjangoPasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:profile')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Heslo bylo změněno.'))
        return response


class UserListView(LoginRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.prefetch_related('user_roles').select_related('company').order_by('username')


class UserCreateView(LoginRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, _('Uživatel byl vytvořen.'))
        return super().form_valid(form)


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, _('Uživatel byl uložen.'))
        return super().form_valid(form)


class CompanyListView(LoginRequiredMixin, ListView):
    model = Company
    template_name = 'accounts/company_list.html'
    context_object_name = 'companies'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)


class CompanyCreateView(LoginRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'accounts/company_form.html'
    success_url = reverse_lazy('accounts:company_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, _('Firma byla vytvořena.'))
        return super().form_valid(form)


class CompanyUpdateView(LoginRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'accounts/company_form.html'
    success_url = reverse_lazy('accounts:company_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, _('Firma byla uložena.'))
        return super().form_valid(form)


class AreaListView(LoginRequiredMixin, ListView):
    model = Area
    template_name = 'accounts/area_list.html'
    context_object_name = 'areas'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Area.objects.prefetch_related('work_categories').all()


class AreaCreateView(LoginRequiredMixin, CreateView):
    model = Area
    form_class = AreaForm
    template_name = 'accounts/area_form.html'
    success_url = reverse_lazy('accounts:area_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, _('Oblast byla vytvořena.'))
        return super().form_valid(form)


class AreaUpdateView(LoginRequiredMixin, UpdateView):
    model = Area
    form_class = AreaForm
    template_name = 'accounts/area_form.html'
    success_url = reverse_lazy('accounts:area_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.has_role(UserRole.ADMIN):
            messages.error(request, _('Nemáte oprávnění.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from apps.tickets.models import WorkCategory
        ctx = super().get_context_data(**kwargs)
        area = self.object
        assigned_pks = set(area.work_categories.values_list('pk', flat=True))
        ctx['all_categories'] = [
            {'cat': cat, 'assigned': cat.pk in assigned_pks}
            for cat in WorkCategory.objects.order_by('name')
        ]
        return ctx

    def form_valid(self, form):
        from apps.tickets.models import WorkCategory
        area = form.save()
        selected_pks = set(int(pk) for pk in self.request.POST.getlist('categories'))
        for cat in WorkCategory.objects.all():
            if cat.pk in selected_pks:
                cat.areas.add(area)
            else:
                cat.areas.remove(area)
        new_name = self.request.POST.get('new_category', '').strip()
        if new_name:
            new_cat = WorkCategory.objects.create(name=new_name)
            new_cat.areas.add(area)
        messages.success(self.request, _('Oblast byla uložena.'))
        return redirect('accounts:area_list')
