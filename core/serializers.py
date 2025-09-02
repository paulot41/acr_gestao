# DRF serializers for public-facing resources of the MVP.
# Keep fields explicit to control API surface and avoid leaking internals.

from __future__ import annotations
from rest_framework import serializers
from .models import (
    Organization,
    Person,
    Membership,
    Product,
    Price,
    Resource,
    ClassTemplate,
    Event,
    Booking,
)


class PersonSerializer(serializers.ModelSerializer):
    # Keep org implicit via middleware; still expose read-only id/name for debugging
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Person
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "nif",
            "phone",
            "notes",
            "organization_name",
        ]


class MembershipSerializer(serializers.ModelSerializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())

    class Meta:
        model = Membership
        fields = [
            "id",
            "person",
            "plan",
            "status",
            "starts_on",
            "ends_on",
        ]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "kind"]


class PriceSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = Price
        fields = ["id", "product", "amount", "currency", "valid_from", "valid_to"]


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ["id", "name", "capacity"]


class ClassTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassTemplate
    # Explicit fields to avoid accidental exposure later
        fields = ["id", "title", "default_capacity", "default_duration_minutes"]


class EventSerializer(serializers.ModelSerializer):
    # Derived fields for convenience
    bookings_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "resource",
            "title",
            "starts_at",
            "ends_at",
            "capacity",
            "bookings_count",
            "is_full",
        ]


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["id", "event", "person", "status", "created_at"]
        read_only_fields = ["created_at"]
