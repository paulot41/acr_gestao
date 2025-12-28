import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.test import override_settings
from core.models import Organization, Person, Resource, Event, Payment


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["org.local"])
def test_summary_data(client):
    org = Organization.objects.create(name="Org", domain="org.local")
    person1 = Person.objects.create(
        organization=org, first_name="A", nif="1", email="a@example.com"
    )
    transaction.set_rollback(False)
    person2 = Person.objects.create(
        organization=org, first_name="B", nif="2", email="b@example.com"
    )
    transaction.set_rollback(False)
    resource = Resource.objects.create(organization=org, name="Room")
    start = timezone.now() + timedelta(days=1)
    Event.objects.create(organization=org, resource=resource, title="E1", starts_at=start, ends_at=start + timedelta(hours=1))
    Payment.objects.create(organization=org, person=person1, amount=100, status=Payment.Status.COMPLETED)
    Payment.objects.create(organization=org, person=person2, amount=50, status=Payment.Status.PENDING)

    user = User.objects.create_user(username="report_user", password="pwd")
    client.force_login(user)

    url = reverse("reports:summary_data")
    response = client.get(url, secure=True, HTTP_HOST='org.local')
    assert response.status_code == 200
    data = response.json()
    assert data["clients"] == 2
    assert data["events"] == 1
    assert data["payments_total"] == 100.0
