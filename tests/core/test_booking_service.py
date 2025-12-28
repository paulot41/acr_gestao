from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import Organization, Person, Resource, Event, Booking
from core.services.bookings import cancel_booking


@pytest.mark.django_db
def test_cancel_booking_denies_unknown_user():
    org = Organization.objects.create(name="Org", domain="example.com")
    user = User.objects.create_user(username="anon", password="pwd")
    person = Person.objects.create(
        organization=org,
        first_name="Ana",
        email="ana@example.com",
        nif="123456789",
    )
    resource = Resource.objects.create(organization=org, name="Room")
    start = timezone.now() + timedelta(hours=3)
    event = Event.objects.create(
        organization=org,
        resource=resource,
        title="Aula",
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        capacity=5,
    )
    booking = Booking.objects.create(organization=org, event=event, person=person)

    result = cancel_booking(booking, user)

    assert result.ok is False
    assert result.status_code == 403


@pytest.mark.django_db
def test_cancel_booking_allows_staff():
    org = Organization.objects.create(name="Org2", domain="example.com")
    staff = User.objects.create_user(username="staff", password="pwd", is_staff=True)
    person = Person.objects.create(
        organization=org,
        first_name="Bea",
        email="bea@example.com",
        nif="987654321",
    )
    resource = Resource.objects.create(organization=org, name="Room2")
    start = timezone.now() + timedelta(hours=3)
    event = Event.objects.create(
        organization=org,
        resource=resource,
        title="Aula",
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        capacity=5,
    )
    booking = Booking.objects.create(organization=org, event=event, person=person)

    result = cancel_booking(booking, staff)

    booking.refresh_from_db()
    assert result.ok is True
    assert result.status_code == 200
    assert booking.status == Booking.Status.CANCELLED


@pytest.mark.django_db
def test_cancel_booking_blocks_too_close():
    org = Organization.objects.create(name="Org3", domain="example.com")
    staff = User.objects.create_user(username="staff2", password="pwd", is_staff=True)
    person = Person.objects.create(
        organization=org,
        first_name="Carla",
        email="carla@example.com",
        nif="555555555",
    )
    resource = Resource.objects.create(organization=org, name="Room3")
    start = timezone.now() + timedelta(hours=1)
    event = Event.objects.create(
        organization=org,
        resource=resource,
        title="Aula",
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        capacity=5,
    )
    booking = Booking.objects.create(organization=org, event=event, person=person)

    result = cancel_booking(booking, staff)

    booking.refresh_from_db()
    assert result.ok is False
    assert result.status_code == 400
    assert booking.status == Booking.Status.CONFIRMED
