from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models as db_models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from apps.accounts.models import UserRole
from .forms import (
    TicketCreateForm, TicketUpdateForm, AssignResolverForm, AssignSalesForm,
    ResolveForm, RejectForm, ChangeTypeForm, CommentForm, TimeLogForm,
    TicketFilterForm,
)
from .models import Ticket, Comment, TimeLog


def _get_adjacent_tickets(user, ticket):
    """Vrátí (prev_pk, next_pk) — sousední tikety ve stejném pořadí jako seznam (dle PK)."""
    qs = Ticket.objects.all()
    if user.has_role(UserRole.MANAGER, UserRole.ADMIN):
        pass
    elif user.has_role(UserRole.RESOLVER):
        qs = qs.filter(resolver=user)
    elif user.has_role(UserRole.SALES):
        qs = qs.filter(sales=user)
    elif user.has_role(UserRole.REQUESTER):
        qs = qs.filter(requester=user)
    else:
        return None, None
    prev_pk = qs.filter(pk__lt=ticket.pk).order_by('-pk').values_list('pk', flat=True).first()
    next_pk = qs.filter(pk__gt=ticket.pk).order_by('pk').values_list('pk', flat=True).first()
    return prev_pk, next_pk


def _can_edit_ticket(user, ticket):
    """Může uživatel editovat tiket (tj. není v uzamčeném stavu)?"""
    if ticket.is_locked:
        return False
    if user.has_role(UserRole.MANAGER):
        return True
    if user.has_role(UserRole.RESOLVER) and ticket.resolver == user:
        return True
    return False


class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'tickets/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.select_related('requester', 'resolver', 'sales', 'company')

        # Filtrování podle role
        if user.has_role(UserRole.MANAGER, UserRole.ADMIN):
            pass  # Správce a admin vidí vše
        elif user.has_role(UserRole.RESOLVER):
            qs = qs.filter(resolver=user)
        elif user.has_role(UserRole.SALES):
            qs = qs.filter(sales=user)
        elif user.has_role(UserRole.REQUESTER):
            qs = qs.filter(requester=user)
        else:
            qs = qs.none()

        # Filtrování z formuláře
        form = TicketFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('status'):
                qs = qs.filter(status=form.cleaned_data['status'])
            if form.cleaned_data.get('type'):
                qs = qs.filter(type=form.cleaned_data['type'])
            if form.cleaned_data.get('area'):
                qs = qs.filter(area=form.cleaned_data['area'])
            if form.cleaned_data.get('priority'):
                qs = qs.filter(priority=form.cleaned_data['priority'])
            if form.cleaned_data.get('search'):
                q = form.cleaned_data['search']
                qs = qs.filter(
                    db_models.Q(title__icontains=q) | db_models.Q(description__icontains=q)
                )

        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['filter_form'] = TicketFilterForm(self.request.GET)
        return ctx


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = 'tickets/ticket_detail.html'

    def get_object(self):
        ticket = get_object_or_404(Ticket, pk=self.kwargs['pk'])
        user = self.request.user
        # Kontrola přístupu
        if user.has_role(UserRole.MANAGER, UserRole.ADMIN):
            return ticket
        if user.has_role(UserRole.RESOLVER) and ticket.resolver == user:
            return ticket
        if user.has_role(UserRole.SALES) and ticket.sales == user:
            return ticket
        if user.has_role(UserRole.REQUESTER) and ticket.requester == user:
            return ticket
        messages.error(self.request, _('Nemáte přístup k tomuto tiketu.'))
        raise PermissionError()

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except PermissionError:
            return redirect('tickets:list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ticket = self.object
        user = self.request.user
        ctx['comment_form'] = CommentForm()
        ctx['timelog_form'] = TimeLogForm()
        ctx['comments'] = ticket.comments.select_related('author').all()
        ctx['time_logs'] = ticket.time_logs.select_related('user').all()
        ctx['resolve_form'] = ResolveForm(instance=ticket)
        ctx['reject_form'] = RejectForm(instance=ticket)
        ctx['assign_resolver_form'] = AssignResolverForm(instance=ticket)
        ctx['assign_sales_form'] = AssignSalesForm(instance=ticket)
        ctx['change_type_form'] = ChangeTypeForm(instance=ticket)
        ctx['can_edit'] = _can_edit_ticket(user, ticket)
        ctx['show_hours'] = user.has_role(UserRole.MANAGER, UserRole.RESOLVER, UserRole.SALES, UserRole.ADMIN)
        prev_pk, next_pk = _get_adjacent_tickets(user, ticket)
        ctx['prev_ticket_pk'] = prev_pk
        ctx['next_ticket_pk'] = next_pk
        return ctx


class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketCreateForm
    template_name = 'tickets/ticket_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        ticket = form.save(commit=False)
        ticket.requester = self.request.user
        user = self.request.user

        # Správce/admin si vybírají firmu ve formuláři, žadatel má svou
        if user.has_role(UserRole.MANAGER, UserRole.ADMIN):
            ticket.company = form.cleaned_data.get('company')
        else:
            ticket.company = user.company

        # Bezpečná kontrola bez přístupu přes FK descriptor
        if not ticket.company_id:
            messages.error(self.request, _('Váš účet nemá přiřazenou firmu. Kontaktujte administrátora.'))
            return self.form_invalid(form)

        ticket.save()
        from apps.notifications.tasks import notify_new_ticket
        notify_new_ticket.delay(ticket.pk)
        messages.success(self.request, _('Tiket byl vytvořen.'))
        return redirect('tickets:detail', pk=ticket.pk)


class TicketUpdateView(LoginRequiredMixin, UpdateView):
    model = Ticket
    form_class = TicketUpdateForm
    template_name = 'tickets/ticket_form.html'

    def dispatch(self, request, *args, **kwargs):
        ticket = get_object_or_404(Ticket, pk=kwargs['pk'])
        if not _can_edit_ticket(request.user, ticket):
            messages.error(request, _('Tiket nelze upravit v aktuálním stavu.'))
            return redirect('tickets:detail', pk=ticket.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        old_type = self.object.type
        ticket = form.save(commit=False)
        if old_type != ticket.type:
            ticket.save()
            ticket.change_type(ticket.type)
        else:
            ticket.save()
        messages.success(self.request, _('Tiket byl uložen.'))
        return redirect('tickets:detail', pk=ticket.pk)


# ------------------------------------------------------------------ #
# HTMX akce                                                           #
# ------------------------------------------------------------------ #

class AssignResolverView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if not request.user.has_role(UserRole.MANAGER):
            return HttpResponse(_('Nedostatečná oprávnění.'), status=403)
        form = AssignResolverForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save(commit=False)
            if ticket.status in (Ticket.STATUS_NEW, Ticket.STATUS_OFFER):
                ticket.to_in_progress()
                ticket.save()
                from apps.notifications.tasks import notify_status_change, notify_assigned_to_resolver
                notify_status_change.delay(ticket.pk)
                notify_assigned_to_resolver.delay(ticket.pk)
            elif ticket.status == Ticket.STATUS_IN_PROGRESS:
                ticket.save()
                from apps.notifications.tasks import notify_assigned_to_resolver
                notify_assigned_to_resolver.delay(ticket.pk)
            messages.success(request, _('Řešitel byl přiřazen.'))
        return redirect('tickets:detail', pk=pk)


class AssignSalesView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if not request.user.has_role(UserRole.MANAGER):
            return HttpResponse(_('Nedostatečná oprávnění.'), status=403)
        if ticket.type != Ticket.TYPE_DEVELOPMENT:
            messages.error(request, _('Obchodníka lze přiřadit pouze k typu „Požadavek na vývoj".'))
            return redirect('tickets:detail', pk=pk)
        form = AssignSalesForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save(commit=False)
            if ticket.status == Ticket.STATUS_NEW:
                ticket.to_offer_prep()
                ticket.save()
                from apps.notifications.tasks import notify_status_change, notify_assigned_to_sales
                notify_status_change.delay(ticket.pk)
                notify_assigned_to_sales.delay(ticket.pk)
            elif ticket.status == Ticket.STATUS_OFFER:
                ticket.save()
                from apps.notifications.tasks import notify_assigned_to_sales
                notify_assigned_to_sales.delay(ticket.pk)
            messages.success(request, _('Obchodník byl přiřazen.'))
        return redirect('tickets:detail', pk=pk)


class ResolveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        can_resolve = (
            request.user.has_role(UserRole.MANAGER) or
            (request.user.has_role(UserRole.RESOLVER) and ticket.resolver == request.user)
        )
        if not can_resolve:
            messages.error(request, _('Nedostatečná oprávnění.'))
            return redirect('tickets:detail', pk=pk)
        form = ResolveForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.to_resolved()
            ticket.save()
            hours_str = request.POST.get('hours', '').strip()
            if hours_str:
                try:
                    hours = float(hours_str)
                    if hours > 0:
                        timelog_user = ticket.resolver if ticket.resolver_id else request.user
                        TimeLog.objects.create(ticket=ticket, user=timelog_user, hours=hours)
                except ValueError:
                    pass
            from apps.notifications.tasks import notify_ticket_closed
            notify_ticket_closed.delay(ticket.pk, closed_as='resolved')
            messages.success(request, _('Tiket byl vyřešen.'))
        else:
            messages.error(request, _('Vyplňte způsob vyřešení.'))
        return redirect('tickets:detail', pk=pk)


class RejectView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if not request.user.has_role(UserRole.MANAGER):
            messages.error(request, _('Nedostatečná oprávnění.'))
            return redirect('tickets:detail', pk=pk)
        form = RejectForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.to_rejected()
            ticket.save()
            from apps.notifications.tasks import notify_ticket_closed
            notify_ticket_closed.delay(ticket.pk, closed_as='rejected')
            messages.success(request, _('Tiket byl zamítnut.'))
        else:
            messages.error(request, _('Vyplňte důvod zamítnutí.'))
        return redirect('tickets:detail', pk=pk)


class ReopenView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if not request.user.has_role(UserRole.MANAGER):
            messages.error(request, _('Nedostatečná oprávnění.'))
            return redirect('tickets:detail', pk=pk)
        target = request.POST.get('target', 'in_progress')
        if target == 'offer_prep' and ticket.type == Ticket.TYPE_DEVELOPMENT:
            ticket.reopen_to_offer_prep()
        else:
            ticket.reopen_to_in_progress()
        ticket.save()
        messages.success(request, _('Tiket byl znovuotevřen.'))
        return redirect('tickets:detail', pk=pk)


class ChangeTypeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if not request.user.has_role(UserRole.MANAGER, UserRole.RESOLVER):
            messages.error(request, _('Nedostatečná oprávnění.'))
            return redirect('tickets:detail', pk=pk)
        form = ChangeTypeForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket.change_type(form.cleaned_data['type'])
            messages.success(request, _('Typ tiketu byl změněn.'))
        return redirect('tickets:detail', pk=pk)


class AddCommentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        # Žadatel může komentovat jen svoje tikety
        if request.user.has_role(UserRole.REQUESTER) and ticket.requester != request.user:
            messages.error(request, _('Nemáte oprávnění komentovat tento tiket.'))
            return redirect('tickets:detail', pk=pk)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.save()
            from apps.notifications.tasks import notify_new_comment
            notify_new_comment.delay(comment.pk)
            if request.htmx:
                return render(request, 'tickets/partials/comment_list.html', {
                    'ticket': ticket,
                    'comments': ticket.comments.select_related('author').all(),
                    'comment_form': CommentForm(),
                })
        return redirect('tickets:detail', pk=pk)


class AddTimeLogView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        can_log = (
            request.user.has_role(UserRole.MANAGER) or
            (request.user.has_role(UserRole.RESOLVER) and ticket.resolver == request.user) or
            (request.user.has_role(UserRole.SALES) and ticket.sales == request.user)
        )
        if not can_log:
            messages.error(request, _('Nemáte oprávnění zapisovat čas.'))
            return redirect('tickets:detail', pk=pk)
        form = TimeLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.ticket = ticket
            log.user = request.user
            log.save()
            messages.success(request, _('Čas byl zapsán.'))
            if request.htmx:
                return render(request, 'tickets/partials/timelog_list.html', {
                    'ticket': ticket,
                    'time_logs': ticket.time_logs.select_related('user').all(),
                })
        return redirect('tickets:detail', pk=pk)
