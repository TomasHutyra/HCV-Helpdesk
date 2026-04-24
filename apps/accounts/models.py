from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class Company(models.Model):
    name = models.CharField(_('název'), max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('firma')
        verbose_name_plural = _('firmy')
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    email = models.EmailField(_('e-mail'), unique=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('firma'),
    )
    language = models.CharField(
        _('jazyk'),
        max_length=2,
        choices=[('cs', 'Čeština'), ('en', 'English')],
        default='cs',
    )

    # ---- Omezení správce ----
    managed_areas = models.ManyToManyField(
        'tickets.Area',
        blank=True,
        related_name='managing_managers',
        verbose_name=_('spravované oblasti'),
        help_text=_('Správce vidí pouze tikety těchto oblastí. Ponechte prázdné pro přístup ke všem oblastem.'),
    )
    managed_companies = models.ManyToManyField(
        'Company',
        blank=True,
        related_name='managing_managers',
        verbose_name=_('spravované firmy'),
        help_text=_('Správce vidí pouze tikety těchto firem. Ponechte prázdné pro přístup ke všem firmám.'),
    )

    # ---- Omezení řešitele ----
    resolver_areas = models.ManyToManyField(
        'tickets.Area',
        blank=True,
        related_name='resolving_resolvers',
        verbose_name=_('oblasti řešitele'),
        help_text=_('Řešitel vidí nové tikety pouze z těchto oblastí. Ponechte prázdné pro přístup ke všem novým tiketům.'),
    )

    # ---- Rozsah viditelnosti žadatele ----
    REQUESTER_SCOPE_OWN = 'own'
    REQUESTER_SCOPE_COMPANY = 'company'
    REQUESTER_SCOPE_COMPANY_AREAS = 'company_areas'
    REQUESTER_SCOPE_CHOICES = [
        ('own', _('Pouze vlastní tikety')),
        ('company', _('Všechny tikety firmy')),
        ('company_areas', _('Tikety firmy v konkrétních oblastech')),
    ]
    requester_scope = models.CharField(
        _('rozsah viditelnosti tiketů'),
        max_length=20,
        choices=REQUESTER_SCOPE_CHOICES,
        default=REQUESTER_SCOPE_OWN,
    )
    requester_areas = models.ManyToManyField(
        'tickets.Area',
        blank=True,
        related_name='requester_users',
        verbose_name=_('oblasti žadatele'),
        help_text=_('Zobrazí se pouze tikety firmy z těchto oblastí. Vlastní tikety jsou viditelné vždy.'),
    )

    class Meta:
        verbose_name = _('uživatel')
        verbose_name_plural = _('uživatelé')

    def __str__(self):
        return self.get_full_name() or self.username

    def has_role(self, *roles):
        return self.user_roles.filter(role__in=roles).exists()

    @property
    def is_requester(self):
        return self.has_role(UserRole.REQUESTER)

    @property
    def is_resolver(self):
        return self.has_role(UserRole.RESOLVER)

    @property
    def is_sales(self):
        return self.has_role(UserRole.SALES)

    @property
    def is_manager(self):
        return self.has_role(UserRole.MANAGER)

    @property
    def is_hcv_admin(self):
        return self.has_role(UserRole.ADMIN)

    def get_roles_display(self):
        return ', '.join(
            self.user_roles.values_list('role', flat=True)
        )

    def get_primary_redirect(self):
        """Kam přesměrovat po přihlášení podle hlavní role."""
        if self.has_role(UserRole.MANAGER, UserRole.ADMIN, UserRole.RESOLVER, UserRole.SALES):
            return '/tickets/'
        return '/tickets/'

    # ------------------------------------------------------------------ #
    # Rozsah viditelnosti žadatele                                        #
    # ------------------------------------------------------------------ #

    def get_requester_ticket_q(self):
        """Vrátí Q výraz pro tikety viditelné žadateli dle jeho rozsahu."""
        from django.db.models import Q
        if self.requester_scope == self.REQUESTER_SCOPE_COMPANY and self.company_id:
            return Q(company_id=self.company_id)
        if self.requester_scope == self.REQUESTER_SCOPE_COMPANY_AREAS and self.company_id:
            area_pks = list(self.requester_areas.values_list('pk', flat=True))
            if area_pks:
                return Q(company_id=self.company_id, area_id__in=area_pks) | Q(requester=self)
        return Q(requester=self)

    def can_see_ticket_as_requester(self, ticket):
        """Ověří (Python), zda žadatel smí vidět daný tiket dle svého rozsahu."""
        if self.requester_scope == self.REQUESTER_SCOPE_COMPANY and self.company_id:
            return ticket.company_id == self.company_id
        if self.requester_scope == self.REQUESTER_SCOPE_COMPANY_AREAS and self.company_id:
            area_pks = set(self.requester_areas.values_list('pk', flat=True))
            if area_pks:
                return (ticket.company_id == self.company_id and ticket.area_id in area_pks) \
                       or ticket.requester_id == self.pk
        return ticket.requester_id == self.pk

    # ------------------------------------------------------------------ #
    # Omezení správce — viditelnost tiketů                                #
    # ------------------------------------------------------------------ #

    def get_ticket_visibility_q(self):
        """
        Vrátí Q výraz pro tikety, které tento správce (s omezeními) vidí.
        Vrátí None, pokud správce nemá žádné omezení (vidí vše).
        Určeno pro ORM filtrování querysetu.
        """
        from django.db.models import Q
        parts = []

        # Oblast: prázdný seznam → bez omezení; "neznámá" oblast se jako omezení nepočítá
        area_pks = list(self.managed_areas.filter(is_unknown=False).values_list('pk', flat=True))
        if area_pks:
            # Tikety s neznámou oblastí nebo bez oblasti jsou vždy zahrnuty
            parts.append(Q(area_id__in=area_pks) | Q(area__is_unknown=True) | Q(area__isnull=True))

        # Firmy
        co_pks = list(self.managed_companies.values_list('pk', flat=True))
        if co_pks:
            parts.append(Q(company_id__in=co_pks))

        if not parts:
            return None
        result = parts[0]
        for p in parts[1:]:
            result &= p
        return result

    def can_see_ticket_as_manager(self, ticket):
        """
        Ověří (na úrovni Pythonu), zda tento správce smí vidět daný tiket.
        Vhodné pro kontrolu přístupu u jednoho tiketu.
        """
        # Oblast
        area_pks = set(self.managed_areas.filter(is_unknown=False).values_list('pk', flat=True))
        if area_pks:
            if ticket.area and not ticket.area.is_unknown and ticket.area_id not in area_pks:
                return False
        # Firmy
        co_pks = set(self.managed_companies.values_list('pk', flat=True))
        if co_pks:
            if ticket.company_id and ticket.company_id not in co_pks:
                return False
        return True

    # ------------------------------------------------------------------ #
    # Omezení řešitele — viditelnost nových tiketů a přiřazení            #
    # ------------------------------------------------------------------ #

    def get_resolver_new_tickets_q(self):
        """
        Vrátí Q výraz omezující nové tikety viditelné tomuto řešiteli dle oblasti.
        Vrátí None, pokud řešitel nemá žádné omezení (vidí všechny nové tikety).
        """
        from django.db.models import Q
        area_pks = list(self.resolver_areas.filter(is_unknown=False).values_list('pk', flat=True))
        if not area_pks:
            return None
        return Q(area_id__in=area_pks) | Q(area__is_unknown=True) | Q(area__isnull=True)

    def can_handle_ticket_area(self, ticket):
        """
        Vrátí True, pokud řešitel může zpracovat tiket dle oblasti
        (tj. oblast tiketu je v jeho oblastech, neznámá nebo prázdná).
        """
        area_pks = set(self.resolver_areas.filter(is_unknown=False).values_list('pk', flat=True))
        if not area_pks:
            return True  # bez omezení
        if ticket.area is None or ticket.area.is_unknown:
            return True
        return ticket.area_id in area_pks


class UserRole(models.Model):
    REQUESTER = 'requester'
    RESOLVER = 'resolver'
    SALES = 'sales'
    MANAGER = 'manager'
    ADMIN = 'admin'

    ROLE_CHOICES = [
        (REQUESTER, _('Žadatel')),
        (RESOLVER, _('Řešitel')),
        (SALES, _('Obchodník')),
        (MANAGER, _('Správce')),
        (ADMIN, _('Administrátor')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        unique_together = ('user', 'role')
        verbose_name = _('role uživatele')
        verbose_name_plural = _('role uživatelů')

    def __str__(self):
        return f'{self.user} — {self.get_role_display()}'
