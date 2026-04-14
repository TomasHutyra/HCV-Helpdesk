from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.generic import ListView, CreateView, UpdateView, TemplateView

from .decorators import role_required
from .forms import LoginForm, UserCreateForm, UserUpdateForm, ProfileForm, CompanyForm
from .models import User, Company, UserRole


class CustomLoginView(LoginView):
    form_class = LoginForm
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        # Nastavit jazyk uživatele
        user = self.request.user
        translation.activate(user.language)
        self.request.session[translation.LANGUAGE_SESSION_KEY] = user.language
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
        # Aktualizovat jazyk po uložení
        lang = form.cleaned_data.get('language', 'cs')
        translation.activate(lang)
        self.request.session[translation.LANGUAGE_SESSION_KEY] = lang
        messages.success(self.request, _('Profil byl uložen.'))
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
