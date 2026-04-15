from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Ticket, Comment, TimeLog


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('type', 'title', 'description', 'area', 'priority')

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].widget = forms.Textarea(attrs={'rows': 5})
        # Správce a admin si mohou vybrat firmu
        if user and user.has_role('manager', 'admin'):
            from apps.accounts.models import Company
            self.fields['company'] = forms.ModelChoiceField(
                queryset=Company.objects.all().order_by('name'),
                label=_('Firma'),
                empty_label=_('— vyberte firmu —'),
            )


class TicketUpdateForm(forms.ModelForm):
    """Pro Řešitele a Správce — mohou měnit typ, prioritu, oblast."""
    class Meta:
        model = Ticket
        fields = ('type', 'title', 'description', 'area', 'priority')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].widget = forms.Textarea(attrs={'rows': 5})


class AssignResolverForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('resolver',)

    def __init__(self, *args, **kwargs):
        from apps.accounts.models import User, UserRole
        super().__init__(*args, **kwargs)
        self.fields['resolver'].queryset = User.objects.filter(
            user_roles__role=UserRole.RESOLVER
        ).distinct()
        self.fields['resolver'].label = _('Řešitel')
        self.fields['resolver'].required = True


class AssignSalesForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('sales',)

    def __init__(self, *args, **kwargs):
        from apps.accounts.models import User, UserRole
        super().__init__(*args, **kwargs)
        self.fields['sales'].queryset = User.objects.filter(
            user_roles__role=UserRole.SALES
        ).distinct()
        self.fields['sales'].label = _('Obchodník')
        self.fields['sales'].required = True


class ResolveForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('resolution_notes',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolution_notes'].label = _('Způsob vyřešení')
        self.fields['resolution_notes'].required = True
        self.fields['resolution_notes'].widget = forms.Textarea(attrs={'rows': 4})


class RejectForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('rejection_reason',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rejection_reason'].label = _('Důvod zamítnutí')
        self.fields['rejection_reason'].required = True
        self.fields['rejection_reason'].widget = forms.Textarea(attrs={'rows': 3})


class ChangeTypeForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('type',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].label = _('Nový typ')


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('body',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].label = _('Komentář')
        self.fields['body'].widget = forms.Textarea(attrs={'rows': 3})


class TimeLogForm(forms.ModelForm):
    class Meta:
        model = TimeLog
        fields = ('hours', 'note')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['hours'].label = _('Hodiny')
        self.fields['note'].label = _('Poznámka')


class TicketFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', _('— vše —'))] + Ticket.STATUS_CHOICES,
        required=False, label=_('Stav'),
    )
    type = forms.ChoiceField(
        choices=[('', _('— vše —'))] + Ticket.TYPE_CHOICES,
        required=False, label=_('Typ'),
    )
    area = forms.ChoiceField(
        choices=[('', _('— vše —'))] + Ticket.AREA_CHOICES,
        required=False, label=_('Oblast'),
    )
    priority = forms.ChoiceField(
        choices=[('', _('— vše —'))] + Ticket.PRIORITY_CHOICES,
        required=False, label=_('Priorita'),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.has_role('manager', 'admin'):
            from apps.accounts.models import Company, User, UserRole
            self.fields['company'] = forms.ModelChoiceField(
                queryset=Company.objects.order_by('name'),
                required=False, label=_('Firma'),
                empty_label=_('— vše —'),
            )
            self.fields['requester'] = forms.ModelChoiceField(
                queryset=User.objects.filter(
                    user_roles__role=UserRole.REQUESTER
                ).distinct().order_by('last_name', 'first_name'),
                required=False, label=_('Žadatel'),
                empty_label=_('— vše —'),
            )
            self.fields['resolver'] = forms.ModelChoiceField(
                queryset=User.objects.filter(
                    user_roles__role=UserRole.RESOLVER
                ).distinct().order_by('last_name', 'first_name'),
                required=False, label=_('Řešitel'),
                empty_label=_('— vše —'),
            )
