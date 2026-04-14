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
