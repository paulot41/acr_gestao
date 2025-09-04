from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .admin import admin_site

router = DefaultRouter()
router.register(r'people', views.PersonViewSet)
router.register(r'memberships', views.MembershipViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'bookings', views.BookingViewSet)

urlpatterns = [
    # API REST
    path('api/', include(router.urls)),

    # Admin Unificado (Custom Admin Site)
    path('admin/', admin_site.urls),

    # Redirect root para admin
    path('', lambda request: __import__('django.shortcuts').shortcuts.redirect('/admin/')),
]
