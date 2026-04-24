from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import User, Company, UserRole
from apps.tickets.models import Area


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label=_('Uživatelské jméno'),
        widget=forms.TextInput(attrs={'class': 'input', 'autofocus': True}),
    )
    password = forms.CharField(
        label=_('Heslo'),
        widget=forms.PasswordInput(attrs={'class': 'input'}),
    )


class UserCreateForm(UserCreationForm):
    roles = forms.MultipleChoiceField(
        choices=UserRole.ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label=_('Role'),
        required=False,
    )
    managed_areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Spravované oblasti'),
        required=False,
        help_text=_('Prázdné = přístup ke všem oblastem.'),
    )
    managed_companies = forms.ModelMultipleChoiceField(
        queryset=Company.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Spravované firmy'),
        required=False,
        help_text=_('Prázdné = přístup ke všem firmám.'),
    )
    resolver_areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Oblasti řešitele'),
        required=False,
        help_text=_('Prázdné = vidí všechny nové tikety.'),
    )
    requester_areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Oblasti žadatele'),
        required=False,
        help_text=_('Zobrazí se pouze tikety firmy z těchto oblastí. Vlastní tikety jsou viditelné vždy.'),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'company', 'language', 'is_active', 'requester_scope')

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserRole.objects.filter(user=user).delete()
            for role in self.cleaned_data.get('roles', []):
                UserRole.objects.create(user=user, role=role)
            user.managed_areas.set(self.cleaned_data.get('managed_areas', []))
            user.managed_companies.set(self.cleaned_data.get('managed_companies', []))
            user.resolver_areas.set(self.cleaned_data.get('resolver_areas', []))
            user.requester_areas.set(self.cleaned_data.get('requester_areas', []))
        return user


class UserUpdateForm(forms.ModelForm):
    roles = forms.MultipleChoiceField(
        choices=UserRole.ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label=_('Role'),
        required=False,
    )
    managed_areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Spravované oblasti'),
        required=False,
        help_text=_('Prázdné = přístup ke všem oblastem.'),
    )
    managed_companies = forms.ModelMultipleChoiceField(
        queryset=Company.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Spravované firmy'),
        required=False,
        help_text=_('Prázdné = přístup ke všem firmám.'),
    )
    resolver_areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Oblasti řešitele'),
        required=False,
        help_text=_('Prázdné = vidí všechny nové tikety.'),
    )
    requester_areas = forms.ModelMultipleChoiceField(
        queryset=Area.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_('Oblasti žadatele'),
        required=False,
        help_text=_('Zobrazí se pouze tikety firmy z těchto oblastí. Vlastní tikety jsou viditelné vždy.'),
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'company', 'language', 'is_active', 'requester_scope')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['roles'] = list(
                self.instance.user_roles.values_list('role', flat=True)
            )
            self.initial['managed_areas'] = list(
                self.instance.managed_areas.values_list('pk', flat=True)
            )
            self.initial['managed_companies'] = list(
                self.instance.managed_companies.values_list('pk', flat=True)
            )
            self.initial['resolver_areas'] = list(
                self.instance.resolver_areas.values_list('pk', flat=True)
            )
            self.initial['requester_areas'] = list(
                self.instance.requester_areas.values_list('pk', flat=True)
            )

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            UserRole.objects.filter(user=user).delete()
            for role in self.cleaned_data.get('roles', []):
                UserRole.objects.create(user=user, role=role)
            user.managed_areas.set(self.cleaned_data.get('managed_areas', []))
            user.managed_companies.set(self.cleaned_data.get('managed_companies', []))
            user.resolver_areas.set(self.cleaned_data.get('resolver_areas', []))
            user.requester_areas.set(self.cleaned_data.get('requester_areas', []))
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'language')


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ('name',)


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ('name', 'is_unknown')
