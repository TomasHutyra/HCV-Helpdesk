from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.TicketListView.as_view(), name='list'),
    path('export/', views.TicketExportView.as_view(), name='export'),
    path('new/', views.TicketCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TicketDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TicketUpdateView.as_view(), name='update'),
    # HTMX akce na tiketu
    path('<int:pk>/assign-resolver/', views.AssignResolverView.as_view(), name='assign_resolver'),
    path('<int:pk>/assign-sales/', views.AssignSalesView.as_view(), name='assign_sales'),
    path('<int:pk>/resolve/', views.ResolveView.as_view(), name='resolve'),
    path('<int:pk>/reject/', views.RejectView.as_view(), name='reject'),
    path('<int:pk>/reopen/', views.ReopenView.as_view(), name='reopen'),
    path('<int:pk>/change-type/', views.ChangeTypeView.as_view(), name='change_type'),
    path('<int:pk>/take/', views.TakeTicketView.as_view(), name='take'),
    path('<int:pk>/comment/', views.AddCommentView.as_view(), name='add_comment'),
    path('<int:pk>/timelog/', views.AddTimeLogView.as_view(), name='add_timelog'),
]
