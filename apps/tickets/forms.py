from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import Ticket, Comment, TimeLog, Area, WorkCategory, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE


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
    """Pro Řešitele a Správce — mohou měnit typ, prioritu, oblast, kategorii práce."""
    class Meta:
        model = Ticket
        fields = ('type', 'title', 'description', 'area', 'priority', 'work_category')

    def __init__(self, *args, area=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].widget = forms.Textarea(attrs={'rows': 5})
        if area and not area.is_unknown:
            qs = WorkCategory.objects.filter(
                Q(areas=area) | Q(areas__isnull=True)
            ).distinct()
        else:
            qs = WorkCategory.objects.all()
        self.fields['work_category'].queryset = qs
        self.fields['work_category'].label = _('Kategorie práce')
        self.fields['work_category'].required = False
        self.fields['work_category'].empty_label = _('— bez kategorie —')


class AssignResolverForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('resolver',)

    def __init__(self, *args, **kwargs):
        from apps.accounts.models import User, UserRole
        super().__init__(*args, **kwargs)
        ticket = self.instance
        resolvers = User.objects.filter(user_roles__role=UserRole.RESOLVER).distinct()
        # Zahrnout pouze řešitele, kteří nemají omezení oblastí,
        # nebo mají oblast tiketu ve svých oblastech (neznámá oblast = bez omezení).
        if ticket and ticket.pk and ticket.area and not ticket.area.is_unknown:
            # Řešitelé BEZ omezení = ti, kteří nemají žádný záznam v resolver_areas
            unrestricted = resolvers.exclude(resolver_areas__isnull=False).distinct()
            # Řešitelé s oblastí tiketu
            with_area = resolvers.filter(resolver_areas=ticket.area).distinct()
            resolvers = (unrestricted | with_area).distinct()
        self.fields['resolver'].queryset = resolvers
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


class MultipleFileInput(forms.FileInput):
    """FileInput s podporou výběru více souborů najednou."""
    allow_multiple_selected = True


class AttachmentUploadForm(forms.Form):
    """Formulář pro nahrání jedné nebo více příloh na detail tiketu."""
    files = forms.FileField(
        label=_('Soubory'),
        widget=MultipleFileInput(attrs={'multiple': True}),
    )

    def clean_files(self):
        # Django při multiple file inputu vrací jen první soubor přes cleaned_data;
        # plný seznam zpracováváme v view přes request.FILES.getlist('files').
        # Zde validujeme alespoň ten první.
        f = self.cleaned_data.get('files')
        if f:
            self._validate_single_file(f)
        return f

    def _validate_single_file(self, f):
        import os
        ext = os.path.splitext(f.name)[1].lower().lstrip('.')
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                _('Nepodporovaný typ souboru .%(ext)s.') % {'ext': ext}
            )
        if f.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(_('Soubor je příliš velký (max 5 MB).'))


class WorkCategoryForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ('work_category',)

    def __init__(self, *args, area=None, **kwargs):
        super().__init__(*args, **kwargs)
        if area and not area.is_unknown:
            qs = WorkCategory.objects.filter(
                Q(areas=area) | Q(areas__isnull=True)
            ).distinct()
        else:
            qs = WorkCategory.objects.all()
        self.fields['work_category'].queryset = qs
        self.fields['work_category'].label = _('Kategorie práce')
        self.fields['work_category'].required = False
        self.fields['work_category'].empty_label = _('— bez kategorie —')


class TicketFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[('', _('— vše —'))] + Ticket.STATUS_CHOICES,
        required=False, label=_('Stav'),
    )
    type = forms.ChoiceField(
        choices=[('', _('— vše —'))] + Ticket.TYPE_CHOICES,
        required=False, label=_('Typ'),
    )
    area = forms.ModelChoiceField(
        queryset=Area.objects.all(),
        required=False, label=_('Oblast'),
        empty_label=_('— vše —'),
    )
    priority = forms.ChoiceField(
        choices=[('', _('— vše —'))] + Ticket.PRIORITY_CHOICES,
        required=False, label=_('Priorita'),
    )
    date_from = forms.DateField(
        required=False, label=_('Vytvořeno od'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d'],
    )
    date_to = forms.DateField(
        required=False, label=_('Vytvořeno do'),
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d'],
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
