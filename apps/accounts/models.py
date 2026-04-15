from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

# Konstanta sdílená s Ticket.AREA_UNKNOWN – duplikována záměrně, aby nebyl
# kruhový import mezi accounts a tickets.
_AREA_UNKNOWN = 'unknown'


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
    MANAGED_AREA_CHOICES = [
        ('it', 'IT'),
        ('helios', 'Helios'),
    ]
    managed_area = models.CharField(
        _('oblast správce'),
        max_length=20,
        blank=True,
        default='',
        choices=MANAGED_AREA_CHOICES,
        help_text=_('Správce vidí pouze tikety dané oblasti. Ponechte prázdné pro přístup ke všem oblastem.'),
    )
    managed_companies = models.ManyToManyField(
        'Company',
        blank=True,
        related_name='managing_managers',
        verbose_name=_('spravované firmy'),
        help_text=_('Správce vidí pouze tikety těchto firem. Ponechte prázdné pro přístup ke všem firmám.'),
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

        # Oblast: prázdná nebo 'unknown' → bez omezení
        if self.managed_area and self.managed_area != _AREA_UNKNOWN:
            # Tikety s neznámou oblastí jsou vždy zahrnuty (bez ohledu na omezení správce)
            parts.append(Q(area=self.managed_area) | Q(area=_AREA_UNKNOWN))

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
        if self.managed_area and self.managed_area != _AREA_UNKNOWN:
            if ticket.area != _AREA_UNKNOWN and self.managed_area != ticket.area:
                return False
        # Firmy
        co_pks = set(self.managed_companies.values_list('pk', flat=True))
        if co_pks:
            if ticket.company_id and ticket.company_id not in co_pks:
                return False
        return True


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
