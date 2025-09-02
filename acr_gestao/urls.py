# Adds DRF router with org-scoped endpoints under /api/.
# Keeps /health/ and /admin/ untouched.

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from core.api import (
    PersonViewSet,
    MembershipViewSet,
    ProductViewSet,
    PriceViewSet,
    ResourceViewSet,
    ClassTemplateViewSet,
    EventViewSet,
    BookingViewSet,
)

def health(_request):
    return JsonResponse({"status": "ok"})

router = DefaultRouter()
router.register(r"persons", PersonViewSet, basename="person")
router.register(r"memberships", MembershipViewSet, basename="membership")
router.register(r"products", ProductViewSet, basename="product")
router.register(r"prices", PriceViewSet, basename="price")
router.register(r"resources", ResourceViewSet, basename="resource")
router.register(r"class-templates", ClassTemplateViewSet, basename="class-template")
router.register(r"events", EventViewSet, basename="event")
router.register(r"bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
