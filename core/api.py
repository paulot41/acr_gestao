# DRF ViewSets with multi-tenant scoping via request.organization.
# Only expose minimal CRUD needed for MVP. Use ModelViewSet for speed.

from __future__ import annotations
from typing import Optional
from rest_framework import viewsets, permissions, mixins
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import QuerySet
from .models import (
    Person,
    Membership,
    Product,
    Price,
    Resource,
    ClassTemplate,
    Event,
    Booking,
)
from .serializers import (
    PersonSerializer,
    MembershipSerializer,
    ProductSerializer,
    PriceSerializer,
    ResourceSerializer,
    ClassTemplateSerializer,
    EventSerializer,
    BookingSerializer,
)

# Basic staff-only policy for now; refine later by role (instructor/admin).
class IsStaff(permissions.BasePermission):
    """Allow access to authenticated staff users only (MVP baseline)."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class OrgScopedMixin:
    """Adds organization scoping to queryset and create() flow."""

    organization_field = "organization"

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org:
            # Filter by organization to enforce tenant boundary
            return qs.filter(**{self.organization_field: org})
        return qs.none()  # No host/organization → no data

    def perform_create(self, serializer):
        org = getattr(self.request, "organization", None)
        # On create, inject organization automatically when the model has it
        if org and self.organization_field in serializer.Meta.model._meta.fields_map:
            serializer.save(**{self.organization_field: org})
        elif org and hasattr(serializer.Meta.model, self.organization_field):
            serializer.save(**{self.organization_field: org})
        else:
            serializer.save()


class PersonViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for people within the current organization."""
    permission_classes = [IsStaff]
    queryset = Person.objects.all().select_related("organization")
    serializer_class = PersonSerializer


class MembershipViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for memberships tied to people in the current organization."""
    permission_classes = [IsStaff]
    queryset = Membership.objects.all().select_related("organization", "person")
    serializer_class = MembershipSerializer


class ProductViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for products offered by the organization."""
    permission_classes = [IsStaff]
    queryset = Product.objects.all().select_related("organization")
    serializer_class = ProductSerializer


class PriceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for prices associated with products."""
    permission_classes = [IsStaff]
    queryset = Price.objects.all().select_related("organization", "product")
    serializer_class = PriceSerializer


class ResourceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for physical/virtual resources (rooms, courts)."""
    permission_classes = [IsStaff]
    queryset = Resource.objects.all().select_related("organization")
    serializer_class = ResourceSerializer


class ClassTemplateViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for default class templates."""
    permission_classes = [IsStaff]
    queryset = ClassTemplate.objects.all().select_related("organization")
    serializer_class = ClassTemplateSerializer


class EventViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for events with conflict validation in model.clean()."""
    permission_classes = [IsStaff]
    queryset = Event.objects.all().select_related("organization", "resource")
    serializer_class = EventSerializer


class BookingViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """CRUD for bookings with capacity validation in model.clean()."""
    permission_classes = [IsStaff]
    queryset = Booking.objects.all().select_related("organization", "event", "person")
    serializer_class = BookingSerializer

    @action(detail=False, methods=["get"])
    def mine(self, request: Request) -> Response:
        """Return bookings filtered by optional person id (?person=)."""
        person_id: Optional[str] = request.query_params.get("person")
        qs = self.get_queryset()
        if person_id:
            qs = qs.filter(person_id=person_id)
        page = self.paginate_queryset(qs)
        if page is not None:
            ser = self.get_serializer(page, many=True)
            return self.get_paginated_response(ser.data)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)
