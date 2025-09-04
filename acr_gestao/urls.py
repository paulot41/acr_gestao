# Adds DRF router with org-scoped endpoints under /api/.
# Keeps /health/ and /admin/ untouched.

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.contrib.auth import views as auth_views

def health(_request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    # Health check (manter para monitorização)
    path('health/', health),

    # Autenticação
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # Tudo através do core (que agora só tem admin unificado)
    path('', include('core.urls')),
]

# Servir ficheiros estáticos e media em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)