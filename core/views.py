from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Person, Membership, Product, Event, Booking
from .serializers import (
    PersonSerializer, MembershipSerializer,
    ProductSerializer, EventSerializer, BookingSerializer
)

class OrganizationMixin:
    """Filtra automaticamente por organização do utilizador."""
    def get_queryset(self):
        return super().get_queryset().filter(organization=self.request.organization)

class PersonViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [permissions.IsAuthenticated]

class EventViewSet(OrganizationMixin, viewsets.ModelViewSet):
    # Corrigir a sintaxe do Count com filter
    queryset = Event.objects.annotate(
        bookings_count=Count('bookings', filter=Q(bookings__status='confirmed'))
    )
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def book(self, request, pk=None):
        """Endpoint para fazer reserva de evento."""
        event = self.get_object()
        # Implementar lógica de booking
        return Response({'status': 'booked'})

class MembershipViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

class ProductViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

class BookingViewSet(OrganizationMixin, viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]