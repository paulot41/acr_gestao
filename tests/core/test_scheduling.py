from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import Organization, Resource, Event


@pytest.mark.django_db
def test_event_overlap_raises_validation_error():
    org = Organization.objects.create(name="Org", domain="org-sched.test")
    resource = Resource.objects.create(organization=org, name="Sala 1", capacity=5)
    start = timezone.now()
    end = start + timedelta(hours=1)

    Event.objects.create(
        organization=org,
        resource=resource,
        title="Aula 1",
        starts_at=start,
        ends_at=end,
        capacity=5,
    )

    event2 = Event(
        organization=org,
        resource=resource,
        title="Aula 2",
        starts_at=start + timedelta(minutes=30),
        ends_at=end + timedelta(minutes=30),
        capacity=5,
    )

    with pytest.raises(ValidationError):
        event2.full_clean()
