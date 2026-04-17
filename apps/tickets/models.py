import os
import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition

ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp',
    'docx', 'xlsx', 'xls', 'pptx', 'ppt', 'odt', 'ods',
    'txt', 'csv', 'log', 'xml', 'json',
    'zip', '7z',
}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


def attachment_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'tickets/attachments/{uuid.uuid4().hex}{ext}'


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


class TicketChange(models.Model):
    """Záznamy o změnách tiketu — audit log."""

    FIELD_CREATED = 'created'
    FIELD_STATUS = 'status'
    FIELD_TYPE = 'type'
    FIELD_PRIORITY = 'priority'
    FIELD_AREA = 'area'
    FIELD_RESOLVER = 'resolver'
    FIELD_SALES = 'sales'
    FIELD_TITLE = 'title'
    FIELD_DESCRIPTION = 'description'
    FIELD_ATTACHMENT_ADDED = 'attachment_added'
    FIELD_ATTACHMENT_DELETED = 'attachment_deleted'
    # Interní pole — skrytá před žadatelem (rezerva pro budoucí záznamy hodin)
    FIELD_TIMELOG = 'timelog'

    INTERNAL_FIELDS = {FIELD_TIMELOG}

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE,
        related_name='history', verbose_name=_('tiket'),
    )
    user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ticket_changes', verbose_name=_('uživatel'),
    )
    field = models.CharField(_('pole'), max_length=30)
    old_value = models.TextField(_('původní hodnota'), blank=True)
    new_value = models.TextField(_('nová hodnota'), blank=True)
    created_at = models.DateTimeField(_('čas'), auto_now_add=True)

    class Meta:
        verbose_name = _('změna tiketu')
        verbose_name_plural = _('změny tiketu')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.ticket} — {self.field}'

    @property
    def description(self):
        if self.field == self.FIELD_CREATED:
            return _('Tiket vytvořen')
        if self.field == self.FIELD_ATTACHMENT_ADDED:
            return f'{_("Příloha přidána")}: {self.new_value}'
        if self.field == self.FIELD_ATTACHMENT_DELETED:
            return f'{_("Příloha smazána")}: {self.new_value}'
        if self.field == self.FIELD_DESCRIPTION:
            return f'{_("Popis upraven")}; {_("původní znění")}: {self.old_value}'
        labels = {
            self.FIELD_STATUS: _('Stav'),
            self.FIELD_TYPE: _('Typ'),
            self.FIELD_PRIORITY: _('Priorita'),
            self.FIELD_AREA: _('Oblast'),
            self.FIELD_RESOLVER: _('Řešitel'),
            self.FIELD_SALES: _('Obchodník'),
            self.FIELD_TITLE: _('Název'),
            self.FIELD_DESCRIPTION: _('Popis'),
        }
        label = labels.get(self.field, self.field)
        if self.old_value:
            return f'{label}: {self.old_value} → {self.new_value}'
        return f'{label}: {self.new_value}'


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE,
        related_name='attachments', verbose_name=_('tiket'),
    )
    file = models.FileField(_('soubor'), upload_to=attachment_upload_path)
    original_name = models.CharField(_('název souboru'), max_length=255)
    uploaded_by = models.ForeignKey(
        'accounts.User', on_delete=models.PROTECT,
        related_name='attachments', verbose_name=_('nahrál'),
    )
    created_at = models.DateTimeField(_('nahráno'), auto_now_add=True)

    class Meta:
        verbose_name = _('příloha')
        verbose_name_plural = _('přílohy')
        ordering = ['created_at']

    def __str__(self):
        return self.original_name

    @property
    def extension(self):
        return os.path.splitext(self.original_name)[1].lower().lstrip('.')

    @property
    def is_image(self):
        return self.extension in {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

    @property
    def size_display(self):
        try:
            size = self.file.size
        except (FileNotFoundError, OSError):
            return ''
        if size < 1024:
            return f'{size} B'
        if size < 1024 * 1024:
            return f'{size / 1024:.0f} KB'
        return f'{size / 1024 / 1024:.1f} MB'
