# Adds DRF router with org-scoped endpoints under /api/.
# Dashboard como página inicial com navegação completa.

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection

def health(_request):
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_ok = False

    status = "ok" if db_ok else "degraded"
    http_status = 200 if db_ok else 503
    return JsonResponse({"status": status, "db": db_ok}, status=http_status)

urlpatterns = [
    # Health check (manter para monitorização)
    path('health/', health),

    # Django Admin padrão
    path('admin/', admin.site.urls),

    path('reports/', include('reports.urls')),
    # Dashboard como página inicial e todas as funcionalidades através do core (namespaced)
    path('', include('core.urls', namespace='core')),
]

# Servir ficheiros estáticos e media em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
