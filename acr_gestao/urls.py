# Adds DRF router with org-scoped endpoints under /api/.
# Keeps /health/ and /admin/ untouched.

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse

def health(_request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health),
    path('api/', include('core.urls')),
    # path('', RedirectView.as_view(url='/admin/')),  # Redirecionar root para admin
]

# Servir ficheiros estáticos em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)