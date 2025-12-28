from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Organization, Person, Resource, Event, Booking, UserProfile


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["example.com"])
def test_cancel_booking_blocks_too_close(client):
    org = Organization.objects.create(name="Org", domain="example.com")
    user = User.objects.create_user(username="client", password="pwd")
    person = Person.objects.create(
        organization=org,
        first_name="Ana",
        email="ana@example.com",
        nif="123456789",
    )
    UserProfile.objects.create(user=user, organization=org, person=person)
    resource = Resource.objects.create(organization=org, name="Room")
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

    client.force_login(user)
    url = reverse("core:api_cancel_booking", args=[booking.id])
    response = client.post(url, secure=True, HTTP_HOST="example.com")

    assert response.status_code == 400
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CONFIRMED


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["example.com"])
def test_cancel_booking_allows_in_window(client):
    org = Organization.objects.create(name="Org2", domain="example.com")
    user = User.objects.create_user(username="client2", password="pwd")
    person = Person.objects.create(
        organization=org,
        first_name="Bea",
        email="bea@example.com",
        nif="987654321",
    )
    UserProfile.objects.create(user=user, organization=org, person=person)
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

    client.force_login(user)
    url = reverse("core:api_cancel_booking", args=[booking.id])
    response = client.post(url, secure=True, HTTP_HOST="example.com")

    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == Booking.Status.CANCELLED
