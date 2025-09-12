from rest_framework import serializers
from .models import Organization, Person, Membership, Product, Event, Booking, Resource


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class PersonSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Person
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'consent_rgpd', 'organization']
        read_only_fields = ['organization']


class MembershipSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.full_name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'person', 'person_name', 'product', 'product_name',
                  'starts_at', 'ends_at', 'is_active', 'organization']
        read_only_fields = ['organization', 'is_active']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'duration_months', 'organization']
        read_only_fields = ['organization']


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = ['id', 'name', 'description', 'capacity', 'organization']
        read_only_fields = ['organization']


class EventSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    bookings_count = serializers.IntegerField(read_only=True)
    available_spots = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'starts_at', 'ends_at',
                  'capacity', 'resource', 'resource_name', 'bookings_count',
                  'available_spots', 'organization']
        read_only_fields = ['organization']

    def get_available_spots(self, obj):
        return obj.capacity - (obj.bookings_count or 0)


class BookingSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.full_name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'person', 'person_name', 'event', 'event_title',
                  'status', 'created_at', 'organization']
        read_only_fields = ['organization', 'created_at']