from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum, Q
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from apps.accounts.models import User, UserRole, Company
from apps.tickets.models import Ticket, TimeLog


def _month_stats_resolver(user, year, month):
    """Statistiky jednoho řešitele za měsíc."""
    tickets = Ticket.objects.filter(
        resolver=user,
        created_at__year=year,
        created_at__month=month,
    )
    time_total = TimeLog.objects.filter(
        user=user,
        created_at__year=year,
        created_at__month=month,
    ).aggregate(total=Sum('hours'))['total'] or 0

    return {
        'user': user,
        'total': tickets.count(),
        'new': tickets.filter(status=Ticket.STATUS_NEW).count(),
        'in_progress': tickets.filter(status=Ticket.STATUS_IN_PROGRESS).count(),
        'resolved': tickets.filter(status=Ticket.STATUS_RESOLVED).count(),
        'rejected': tickets.filter(status=Ticket.STATUS_REJECTED).count(),
        'time_total': float(time_total),
    }


def _month_stats_company(company, year, month):
    """Statistiky firmy za měsíc."""
    tickets = Ticket.objects.filter(
        company=company,
        created_at__year=year,
        created_at__month=month,
    )
    open_statuses = [Ticket.STATUS_NEW, Ticket.STATUS_OFFER, Ticket.STATUS_IN_PROGRESS]
    time_total = TimeLog.objects.filter(
        ticket__company=company,
        created_at__year=year,
        created_at__month=month,
    ).aggregate(total=Sum('hours'))['total'] or 0

    return {
        'company': company,
        'total': tickets.count(),
        'open': tickets.filter(status__in=open_statuses).count(),
        'resolved': tickets.filter(status=Ticket.STATUS_RESOLVED).count(),
        'rejected': tickets.filter(status=Ticket.STATUS_REJECTED).count(),
        'time_total': float(time_total),
    }


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'stats/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.has_role(UserRole.MANAGER, UserRole.RESOLVER, UserRole.SALES):
            messages.error(request, _('Statistiky nejsou dostupné pro vaši roli.'))
            return redirect('tickets:list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = date.today()
        year = int(self.request.GET.get('year', today.year))
        month = int(self.request.GET.get('month', today.month))

        # Navigace měsíců
        if month == 1:
            prev_year, prev_month = year - 1, 12
        else:
            prev_year, prev_month = year, month - 1
        if month == 12:
            next_year, next_month = year + 1, 1
        else:
            next_year, next_month = year, month + 1

        month_names = [
            '', 'Leden', 'Únor', 'Březen', 'Duben', 'Květen', 'Červen',
            'Červenec', 'Srpen', 'Září', 'Říjen', 'Listopad', 'Prosinec',
        ]
        ctx.update({
            'year': year,
            'month': month,
            'month_name': month_names[month],
            'prev_year': prev_year, 'prev_month': prev_month,
            'next_year': next_year, 'next_month': next_month,
        })

        user = self.request.user

        if user.has_role(UserRole.MANAGER):
            # Správce: přehled všech řešitelů + firem
            resolvers = User.objects.filter(
                user_roles__role=UserRole.RESOLVER, is_active=True
            ).distinct()
            ctx['resolver_stats'] = [
                _month_stats_resolver(r, year, month) for r in resolvers
            ]
            companies = Company.objects.all()
            ctx['company_stats'] = [
                _month_stats_company(c, year, month) for c in companies
            ]
        else:
            # Řešitel / obchodník: jen vlastní statistiky
            ctx['my_stats'] = _month_stats_resolver(user, year, month)

        return ctx
