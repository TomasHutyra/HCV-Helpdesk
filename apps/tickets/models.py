from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition


class Area(models.Model):
    name = models.CharField(_('název'), max_length=100)
    is_unknown = models.BooleanField(
        _('neznámá oblast'), default=False,
        help_text=_('Tikety s touto oblastí nejsou omezeny oblastí správce.'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('oblast')
        verbose_name_plural = _('oblasti')
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def get_unknown(cls):
        """Vrátí oblast označenou jako neznámá (pro e-mailové tikety)."""
        return cls.objects.filter(is_unknown=True).first()


class Ticket(models.Model):
    # --- Typy tiketů ---
    TYPE_PROBLEM = 'problem'
    TYPE_DEVELOPMENT = 'development'
    TYPE_IMPROVEMENT = 'improvement'

    TYPE_CHOICES = [
        (TYPE_PROBLEM, _('Hlášení problému')),
        (TYPE_DEVELOPMENT, _('Požadavek na vývoj')),
        (TYPE_IMPROVEMENT, _('Námět na zlepšení')),
    ]

    # --- Stavy ---
    STATUS_NEW = 'new'
    STATUS_OFFER = 'offer_prep'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_RESOLVED = 'resolved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_NEW, _('Nový')),
        (STATUS_OFFER, _('Příprava nabídky')),
        (STATUS_IN_PROGRESS, _('Řeší se')),
        (STATUS_RESOLVED, _('Vyřešeno')),
        (STATUS_REJECTED, _('Zamítnuto')),
    ]

    # Platné stavy pro každý typ
    VALID_STATUSES = {
        TYPE_PROBLEM:     {STATUS_NEW, STATUS_IN_PROGRESS, STATUS_RESOLVED, STATUS_REJECTED},
        TYPE_DEVELOPMENT: {STATUS_NEW, STATUS_OFFER, STATUS_IN_PROGRESS, STATUS_RESOLVED, STATUS_REJECTED},
        TYPE_IMPROVEMENT: {STATUS_NEW, STATUS_REJECTED},
    }

    # --- Priorita ---
    PRIORITY_HIGH = 'high'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_LOW = 'low'

    PRIORITY_CHOICES = [
        (PRIORITY_HIGH, _('Vysoká')),
        (PRIORITY_MEDIUM, _('Střední')),
        (PRIORITY_LOW, _('Nízká')),
    ]

    # --- Pole ---
    type = models.CharField(_('typ'), max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(_('název'), max_length=200)
    description = models.TextField(_('popis'))
    area = models.ForeignKey(
        'Area', on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='tickets', verbose_name=_('oblast'),
    )
    priority = models.CharField(_('priorita'), max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = FSMField(_('stav'), default=STATUS_NEW, protected=True, choices=STATUS_CHOICES)

    company = models.ForeignKey(
        'accounts.Company', on_delete=models.PROTECT,
        related_name='tickets', verbose_name=_('firma'),
    )
    requester = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT,
        related_name='requested_tickets', verbose_name=_('žadatel'),
    )
    resolver = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_tickets', verbose_name=_('řešitel'),
    )
    sales = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sales_tickets', verbose_name=_('obchodník'),
    )

    resolution_notes = models.TextField(_('způsob vyřešení'), blank=True)
    rejection_reason = models.TextField(_('důvod zamítnutí'), blank=True)

    created_at = models.DateTimeField(_('vytvořeno'), auto_now_add=True)
    updated_at = models.DateTimeField(_('upraveno'), auto_now=True)
    resolved_at = models.DateTimeField(_('vyřešeno dne'), null=True, blank=True)

    class Meta:
        verbose_name = _('tiket')
        verbose_name_plural = _('tikety')
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.pk} {self.title}'

    # ------------------------------------------------------------------ #
    # Stavový automat — přechody                                           #
    # ------------------------------------------------------------------ #

    @transition(field=status, source=STATUS_NEW, target=STATUS_OFFER)
    def to_offer_prep(self):
        """Přiřadit obchodníka → Příprava nabídky (pouze typ Vývoj)."""
        pass

    @transition(field=status, source=[STATUS_NEW, STATUS_OFFER], target=STATUS_IN_PROGRESS)
    def to_in_progress(self):
        """Přiřadit řešitele → Řeší se."""
        pass

    @transition(field=status, source=STATUS_IN_PROGRESS, target=STATUS_RESOLVED)
    def to_resolved(self):
        """Vyřešit → Vyřešeno (vyžaduje resolution_notes a čas)."""
        self.resolved_at = timezone.now()

    @transition(field=status, source=[STATUS_NEW, STATUS_OFFER, STATUS_IN_PROGRESS], target=STATUS_REJECTED)
    def to_rejected(self):
        """Zamítnout → Zamítnuto (vyžaduje rejection_reason)."""
        pass

    @transition(field=status, source=[STATUS_RESOLVED, STATUS_REJECTED], target=STATUS_IN_PROGRESS)
    def reopen_to_in_progress(self):
        """Znovuotevřít → Řeší se."""
        self.resolved_at = None

    @transition(field=status, source=[STATUS_RESOLVED, STATUS_REJECTED], target=STATUS_OFFER)
    def reopen_to_offer_prep(self):
        """Znovuotevřít → Příprava nabídky (pouze typ Vývoj)."""
        self.resolved_at = None

    # ------------------------------------------------------------------ #
    # Pomocné metody                                                       #
    # ------------------------------------------------------------------ #

    def change_type(self, new_type):
        """Změní typ tiketu a případně resetuje stav na Nový."""
        valid = self.VALID_STATUSES.get(new_type, set())
        if self.status not in valid:
            # Obejde FSM ochranu pouze pro reset stavu při změně typu
            Ticket.objects.filter(pk=self.pk).update(status=self.STATUS_NEW)
            self.status = self.STATUS_NEW
        self.type = new_type
        self.save()

    @property
    def is_locked(self):
        """Vyřešeno a Zamítnuto jsou jen pro čtení (kromě znovuotevření)."""
        return self.status in (self.STATUS_RESOLVED, self.STATUS_REJECTED)

    def total_hours(self):
        return self.time_logs.aggregate(
            total=models.Sum('hours')
        )['total'] or 0

    def get_status_color(self):
        return {
            self.STATUS_NEW: 'gray',
            self.STATUS_OFFER: 'purple',
            self.STATUS_IN_PROGRESS: 'blue',
            self.STATUS_RESOLVED: 'green',
            self.STATUS_REJECTED: 'red',
        }.get(self.status, 'gray')

    def get_priority_color(self):
        return {
            self.PRIORITY_HIGH: 'red',
            self.PRIORITY_MEDIUM: 'amber',
            self.PRIORITY_LOW: 'green',
        }.get(self.priority, 'gray')


class Comment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE,
        related_name='comments', verbose_name=_('tiket'),
    )
    author = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT,
        related_name='comments', verbose_name=_('autor'),
    )
    body = models.TextField(_('text'))
    created_at = models.DateTimeField(_('vytvořeno'), auto_now_add=True)

    class Meta:
        verbose_name = _('komentář')
        verbose_name_plural = _('komentáře')
        ordering = ['created_at']

    def __str__(self):
        return f'Komentář #{self.pk} k {self.ticket}'


class TimeLog(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE,
        related_name='time_logs', verbose_name=_('tiket'),
    )
    user = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT,
        related_name='time_logs', verbose_name=_('uživatel'),
    )
    hours = models.DecimalField(_('hodiny'), max_digits=5, decimal_places=2)
    note = models.CharField(_('poznámka'), max_length=200, blank=True)
    created_at = models.DateTimeField(_('vytvořeno'), auto_now_add=True)

    class Meta:
        verbose_name = _('časový záznam')
        verbose_name_plural = _('časové záznamy')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.hours}h — {self.ticket}'
