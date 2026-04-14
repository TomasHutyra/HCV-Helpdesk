from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('tickets/', include('apps.tickets.urls', namespace='tickets')),
    path('stats/', include('apps.stats.urls', namespace='stats')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('', RedirectView.as_view(url='/tickets/', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
