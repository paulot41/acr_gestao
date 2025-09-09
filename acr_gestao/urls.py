# Adds DRF router with org-scoped endpoints under /api/.
# Dashboard como página inicial com navegação completa.

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health(_request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    # Health check (manter para monitorização)
    path('health/', health),

    # Django Admin padrão
    path('admin/', admin.site.urls),

    # Dashboard como página inicial e todas as funcionalidades através do core
    path('', include('core.urls')),
]

# Servir ficheiros estáticos e media em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)