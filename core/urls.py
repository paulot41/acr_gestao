from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'people', views.PersonViewSet)
router.register(r'memberships', views.MembershipViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'bookings', views.BookingViewSet)

urlpatterns = [
    path('', include(router.urls)),
]