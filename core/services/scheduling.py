# Scheduling validations without importing models at module import time
# to avoid circular imports with core.models.

from __future__ import annotations
from django.apps import apps
from django.db.models import Q
from django.core.exceptions import ValidationError


def _Event():
    """Lazy model getter to break import cycles."""
    return apps.get_model("core", "Event")


def _Booking():
    """Lazy model getter to break import cycles."""
    return apps.get_model("core", "Booking")


def ensure_no_conflict(event) -> None:
    """Raise if there is any overlapping event on the same resource."""
    Event = _Event()
    qs = Event.objects.filter(
        organization=event.organization, resource=event.resource
    ).exclude(pk=event.pk)
    overlap = qs.filter(
        Q(starts_at__lt=event.ends_at) & Q(ends_at__gt=event.starts_at)
    ).exists()
    if overlap:
        raise ValidationError("Conflict: another event overlaps on this resource.")


def ensure_capacity(booking) -> None:
    """Raise if event capacity would be exceeded by this booking."""
    ev = booking.event
    # Use model property; counts non-cancelled bookings
    if ev.is_full and booking.status != "cancelled":
        raise ValidationError("Capacity reached for this event.")
