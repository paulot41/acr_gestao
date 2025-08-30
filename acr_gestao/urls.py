# acr_gestao/urls.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # root → admin (podes trocar depois para um dashboard/home)
    path("", lambda request: redirect("/admin/", permanent=False)),
    path("admin/", admin.site.urls),
]

# servir media em dev / staging (Caddy/Gunicorn podem servir isto em prod)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
