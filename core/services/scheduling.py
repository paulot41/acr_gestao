from __future__ import annotations
from django.core.exceptions import ValidationError
from django.db.models import Q
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import Event, Booking


def ensure_no_conflict(event: 'Event') -> None:
    """Validate that the event doesn't overlap with existing events on the same resource."""
    if not event.resource:
        return

    # Get conflicting events (overlapping time ranges on same resource)
    conflicting_events = event.__class__.objects.filter(
        resource=event.resource,
        organization=event.organization
    ).exclude(pk=event.pk if event.pk else None).filter(
        Q(starts_at__lt=event.ends_at) & Q(ends_at__gt=event.starts_at)
    )

    if conflicting_events.exists():
        conflict = conflicting_events.first()
        raise ValidationError(
            f"Event conflicts with '{conflict.title}' "
            f"({conflict.starts_at:%H:%M}-{conflict.ends_at:%H:%M})"
        )


def ensure_capacity(booking: 'Booking') -> None:
    """Validate that booking doesn't exceed event capacity."""
    if not booking.event or booking.status == 'cancelled':
        return

    # Count confirmed bookings (excluding this one if updating)
    confirmed_bookings = booking.event.bookings.filter(
        status='confirmed'
    ).exclude(pk=booking.pk if booking.pk else None).count()

    # Check if adding this booking would exceed capacity
    if confirmed_bookings >= booking.event.capacity:
        raise ValidationError(
            f"Event '{booking.event.title}' is full "
            f"({confirmed_bookings}/{booking.event.capacity})"
        )